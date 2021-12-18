from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from folium.features import Choropleth
from folium.map import Tooltip
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import folium
import json
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

global df

# Gather Data and Process


def get_data_and_process():
    # Get data and store to DF
    url_part = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/rolling-averages/us-counties-recent.csv'
    df = pd.read_csv(url_part)
    # Store copy of original
    original_df = df
    # Drop all but the most recent data (yesterday)
    yesterday = date.today() - timedelta(days=1)
    df = df.loc[(df['date'] == str(yesterday))]
    # Add column for potential risk
    df['potential_risk'] = round(
        (df['cases']/df['cases_avg_per_100k'])/100000*100, 4)
    # Drop null
    df = df.dropna()
    # Group by county to get the top 15 for each map we will be building
    top_fifteen_cases = df.nlargest(15, 'cases')[['county', 'cases']]
    top_fifteen_100k = df.nlargest(15, 'cases_avg_per_100k')[
        ['county', 'cases_avg_per_100k']]
    top_fifteen_risk = df.nlargest(15, 'potential_risk')[
        ['county', 'potential_risk']]
    return top_fifteen_cases, top_fifteen_100k, top_fifteen_risk, df, original_df

# Create map of top cases


def create_cases_map(updated):
    with open('gz_2010_us_050_00_500k.json') as f:
        geojson_counties = json.load(f)
    for i in geojson_counties['features']:
        i['id'] = i['properties']['NAME']
    cases_map = folium.Map(location=[48, -102], zoom_start=4)
    folium.Choropleth(
        geo_data=geojson_counties,
        name='choropleth',
        data=updated,
        columns=['county', 'cases'],
        key_on='feature.id',
        fill_color='YlOrRd',
        fill_opacity=0.5,
        line_opacity=0.1,
        legend_name='Total Covid Cases',
        bins=[float(x) for x in value_bins],
        highlight=True
    ).add_to(cases_map)
    return cases_map

# Create map of top 100k cases


def create_average_map(df):
    with open('gz_2010_us_050_00_500k.json') as f:
        geojson_counties = json.load(f)
    for i in geojson_counties['features']:
        i['id2'] = i['properties']['NAME']
    average_map = folium.Map(location=[48, -102], zoom_start=4)
    folium.Choropleth(
        geo_data=geojson_counties,
        name='choropleth',
        data=df,
        columns=['county', 'cases_avg_per_100k'],
        key_on='feature.id2',
        fill_color='YlOrRd',
        fill_opacity=0.5,
        line_opacity=0.1,
        legend_name='Average Infected Per 100k',
        highlight=True
    ).add_to(average_map)
    return average_map

# Create potential risk map


def create_risk_map(updated):
    with open('gz_2010_us_050_00_500k.json') as f:
        geojson_counties = json.load(f)
    for i in geojson_counties['features']:
        i['id3'] = i['properties']['NAME']
    risk_map = folium.Map(location=[48, -102], zoom_start=4)
    folium.Choropleth(
        geo_data=geojson_counties,
        name='choropleth',
        data=updated,
        columns=['county', 'potential_risk'],
        key_on='feature.id3',
        fill_color='YlOrRd',
        fill_opacity=0.5,
        line_opacity=0.1,
        legend_name='Potential Risk of Becoming Infected',
        bins=[float(x) for x in potential_bins],
        highlight=True
    ).add_to(risk_map)
    return risk_map

# Create 30 day line chart


def create_30_day(original_df):
    original_df['date'] = pd.to_datetime(
        original_df['date'], format='%Y-%m-%d')
    grouped = original_df.groupby('date').sum()['cases']
    # plot line graph of 30 days and save to foo.png to call upon later
    my_path = os.path.dirname(os.path.dirname(__file__))
    plt.plot(grouped)
    plt.xticks(color='w')
    plt.tick_params(bottom=False)
    plt.xlabel('Past 30 days')
    plt.ylabel('Cases Reported')
    plt.savefig(my_path + '\\final_covid\\static\\uploads\\line.png')


# Code executes the above functions and stores variables for flask web page
# Store all data frame variables
top_fifteen_cases, top_fifteen_100k, top_fifteen_risk, df, original_df = get_data_and_process()
updated = df[df['cases'] >= 0]
updated.replace([np.inf, -np.inf], np.nan, inplace=True)
updated.dropna()
#0, 0.60, 0.95, 0.999, 1
value_bins = [updated['cases'].min(), updated['cases'].nlargest(448).iloc[-1], updated['cases'].nlargest(223).iloc[-1], updated['cases'].nlargest(120).iloc[-1],
              updated['cases'].nlargest(57).iloc[-1], updated['cases'].nlargest(29).iloc[-1], updated['cases'].nlargest(7).iloc[-1], updated['cases'].max()]
potential_bins = [updated['potential_risk'].min(), updated['potential_risk'].nlargest(448).iloc[-1], updated['potential_risk'].nlargest(223).iloc[-1], updated['potential_risk'].nlargest(120).iloc[-1],
                  updated['potential_risk'].nlargest(57).iloc[-1], updated['potential_risk'].nlargest(29).iloc[-1], updated['potential_risk'].nlargest(7).iloc[-1], updated['potential_risk'].max()]


# bins = list(updated['cases'].quantile(
# [0, 0.50, 0.60, 0.70, 0.80, 0.85, 0.88, 0.90, 0.999, 1]))
# bins_potential = list(
# updated['potential_risk'].quantile([0, 0.60, 0.90, 0.95, 0.9999, 1]))

# Creating the 15 top counties per category to pass to webpage
case_pairs = [(county, cases)
              for county, cases in zip(top_fifteen_cases['county'], top_fifteen_cases['cases'])]
hundred_pairs = [(county, cases_avg_per_100k)
                 for county, cases_avg_per_100k in zip(top_fifteen_100k['county'], top_fifteen_100k['cases_avg_per_100k'])]
risk_pairs = [(county, potential_risk)
              for county, potential_risk in zip(top_fifteen_risk['county'], top_fifteen_risk['potential_risk'])]

# Replace infinite values with null and drop null
updated.replace([np.inf, -np.inf], np.nan, inplace=True)
updated.dropna()
# Create all map variables to pass to flask webpage
cases_map = create_cases_map(updated)
html_cases_map = cases_map._repr_html_()
average_map = create_average_map(updated)
html_average_map = average_map._repr_html_()
risk_map = create_risk_map(updated)
html_risk_map = risk_map._repr_html_()
create_30_day(original_df)


UPLOAD = os.path.join('static', 'uploads')
# Below is the flask that runs the web page
app = Flask(__name__)
# Create .db file using sqlite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = UPLOAD
# initialized database
db = SQLAlchemy(app)

# Create the database


class Users(db.Model):
    id = db.Column('user_id', db.Integer, primary_key=True)
    fname = db.Column(db.String(200))
    lname = db.Column(db.String(200))
    email = db.Column(db.String)
    county = db.Column(db.String)
    state = db.Column(db.String)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, fname, lname, email, county, state):
        self.fname = fname
        self.lname = lname
        self.email = email
        self.county = county
        self.state = state

# Index Page (Initial Load)


@app.route('/')
def index():
    title = "Home Page"
    return render_template("home.html", title=title)

# Home page


@app.route('/home')
def home():
    title = "Home Page"
    return render_template("home.html", title=title)

# Map of total cases page


@app.route('/total')
def total():
    title = "Total Cases"
    return render_template("total.html", title=title, table=top_fifteen_cases, cmap=html_cases_map, pairs=case_pairs)

# Map of 100k cases


@app.route('/100k')
def onehundredk():
    title = "Cases Per 100k"
    return render_template("100k.html", title=title, table=top_fifteen_100k, cmap=html_average_map, pairs=hundred_pairs)

# Map of potential cases


@app.route('/potential')
def potential():
    title = "Potential Risk"
    return render_template("potential.html", title=title, table=top_fifteen_risk, cmap=html_risk_map, pairs=risk_pairs)

# Map of 30 day line graph


@app.route('/line')
def line():
    title = "Line Graph"
    full_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'line.png')
    return render_template("line.html", title=title, user_image=full_filename)

# Email list


@app.route('/email')
def email():
    title = "Email list"
    users = Users.query.order_by(Users.date_created)
    return render_template("email.html", title=title, users=users)

# Subscribe list


@app.route('/subscribe')
def subscribe():
    title = "Subscribe To Email"
    return render_template("subscribe.html", title=title)

# Storing data to database on sign up and sending confirmation email


@app.route('/subscribeform', methods=["POST"])
def subscribeform():
    # Create a list of states and counties
    state_names = ["Alaska", "Alabama", "Arkansas", "American Samoa", "Arizona", "California", "Colorado", "Connecticut", "District ", "of Columbia", "Delaware", "Florida", "Georgia", "Guam", "Hawaii", "Iowa", "Idaho", "Illinois", "Indiana", "Kansas", "Kentucky", "Louisiana", "Massachusetts", "Maryland", "Maine", "Michigan", "Minnesota", "Missouri", "Mississippi",
                   "Montana", "North Carolina", "North Dakota", "Nebraska", "New Hampshire", "New Jersey", "New Mexico", "Nevada", "New York", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Puerto Rico", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Virginia", "Virgin Islands", "Vermont", "Washington", "Wisconsin", "West Virginia", "Wyoming"]
    county_names = list(df.county.unique())
    # Store form values in variables to later commit to database of users
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    county = request.form.get("county")
    state = request.form.get("state")

    # Check all fields are entered
    if not first_name or not last_name or not email or not county or not state:
        error_statement = "All form fields required"
        return render_template("fail.html", error_statement=error_statement)
    # Confirm state is spelled correctly
    if state.title() not in state_names:
        error_statement = "Please enter full name of state (California) and double check spelling."
        return render_template("fail.html", error_statement=error_statement)
    # Confirm county is spelled correctly
    if county.title() not in county_names:
        error_statement = "Please enter full name of county (Orange), omit the word 'county', and double check spelling. Orange County should be input as 'Orange'"
        return render_template("fail.html", error_statement=error_statement)
    # Check if email is already in use
    user = Users.query.filter_by(email=email).first()
    if not user:
        # Email does not exist
        pass
    else:
        error_statement = "Email already in use please enter a new email address"
        return render_template("fail.html", error_statement=error_statement)

    # adding variables to database
    user = Users(first_name, last_name, email, county, state)
    # Push and commit to database
    try:
        db.session.add(user)
        db.session.commit()
    except:
        return "Error committing to database"

    # using gmail as sending server

    # Create message template for first auto mated email
    today = date.today()
    msg = MIMEText("You are subscribed for covid 19 updates!")
    msg['Subject'] = f"Subscription Successful, {today}"
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    # Log into burner email, in a real world applicatio you would use an inviornmental variable. This is different per OS so making a burner email.
    server.login("isdscovidproject@gmail.com", "BasicPassword123")
    server.sendmail("isdscovidproject@gmail.com", email, msg.as_string())

    title = "Thank You!"
    return render_template("subscribeform.html", title=title)

# Page for user to request update


@app.route('/requestpage')
def requestpage():
    title = "Request update"
    return render_template("requestpage.html", title=title)


@app.route('/requestform', methods=["POST"])
def requestform():
    # get email that we want to push an upate to

    email = request.form.get("email_request")
    user = Users.query.filter_by(email=email).first()
    if user is None:
        return "Error sending email. It is either not in the database or you mistyped it. Please hit the back button and retry."
    else:
        today = date.today()
        # find county in database
        found = df.loc[(df['county'] == user.county.title())
                       & (df['state'] == user.state.title())]
        found = found.drop('date', 1)
        found = found.drop('geoid', 1)
        found = found.drop('cases_avg', 1)
        found = found.drop('deaths_avg', 1)
        found.reset_index(drop=True, inplace=True)
        msg = MIMEMultipart()
        msg['Subject'] = f"Requested update for {today}"
        html = """\
        <html>
        <head></head>
        <body>
            Hello {0} {1}! The below information is the most recent data for Covid 19 per your request. The data is yesterdays reported numbers. {2}
        </body>
        </html>
        """.format(user.fname, user.lname, found.to_html())
        part1 = MIMEText(html, 'html')
        msg.attach(part1)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        # Log into burner email, in a real world applicatio you would use an inviornmental variable. This is different per OS so making a burner email.
        server.login("isdscovidproject@gmail.com", "BasicPassword123")
        server.sendmail("isdscovidproject@gmail.com", email, msg.as_string())

    title = "Request Sent"
    return render_template("requestform.html", title=title)


@app.route('/unsubscribe')
def unsubscribe():
    title = "Unsubscribe"
    return render_template("unsubscribe.html", title=title)


@app.route('/unsubscribeform', methods=["POST"])
def unsubscribeform():
    email_get = request.form.get("email_remove")
    user = Users.query.filter_by(email=email_get).first()
    # Delete if in database otherwise error out
    if user is None:
        return "No email that matches input email in dataset. Please press the back button to continue."
    else:
        try:
            db.session.delete(user)
            db.session.commit()
        except:
            error_statement = "Email does not exist in database."
            return render_template("unsubscribefail.html", error_statement=error_statement)

    title = "Unsubscribes"
    return render_template("unsubscribeform.html", title=title)


if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
