'''
Simple Flask application to test deployment to Amazon Web Services
Uses Elastic Beanstalk

'''

from flask import Flask, render_template, request, jsonify
from StringIO import StringIO
from zipfile import ZipFile
from urllib import urlopen
from datetime import time
from dateutil.parser import parse
import datetime
import requests
import csv
import p2p
import sys
import os
from p2p import P2PException

# Elastic Beanstalk initalization
application = Flask(__name__)
application.debug = True

def to_end_of_list(sorted_list, values):
    try:
        for value in values:
            sorted_list.remove(value)
            sorted_list.append(value)

    except ValueError:
        pass

def process_points(redo=False):
    """
    Geocodes and applies filters, generating an updated csv.
    """
    file_name = "original"
    if redo:
        file_name = "geocoded"

    #Open the new CSV to read from it
    row_list = csv.DictReader(open(file_name+"-"+date_string+".csv", "r"))

    #We only want dates since last wednesday at midnight, so let's parse those out
    last_week = []
    p2p_points = []
    today = datetime.datetime.today()
    sinceLastWednesday = today - datetime.timedelta(days=today.weekday() - 2, weeks=1)
    sinceLastWednesday = sinceLastWednesday.replace(hour=0, minute=0, second=0, microsecond=0)
    for row in row_list:
        dt = parse(row['activityDate'])
        if dt >= sinceLastWednesday or redo:
            # If this is a valid date, hit the Bing API to get the lat/long
            if row['BLOCK_ADDRESS']:
                try:
                    print "OK: Getting lat/long for " + row['BLOCK_ADDRESS']
                    payload = {
                        "addressLine": str(row['BLOCK_ADDRESS']), 
                        "key": "AqEQ_HqipMZe_KnMeHEJ_CEtkNG9Y34_aXaGeIya4fBtc4hTIA9KYzMfFaK5nbK5"
                    }
                    #Add zipcode if it exists
                    if row['ZipCode']:
                        payload['postalCode'] = str(row['ZipCode'])[:5]
                    
                    #Run the actual request through the API
                    r = requests.get("http://dev.virtualearth.net/REST/v1/Locations", payload)
                    response = r.json()
                    coords = response['resourceSets'][0]['resources'][0]['point']['coordinates']
                    confidence = response['resourceSets'][0]['resources'][0]['confidence']
                except Exception:
                    print "WARN: No point could be geocoded for this address (" + row['BLOCK_ADDRESS'] + ")"
                    coords = ["NONE", "NONE"]
            else: 
                print "WARN: No block address to geocode!"
                coords = ["NONE", "NONE"]

            row['lat'] = coords[0]
            row['long'] = coords[1]
            row['confidence'] = confidence

            #Look on the charge and try to categorize
            charge_text = row['Charge_Description_Orig'].lower()

            #Defaults set first
            crime_type = "Other"
            point_color = "white"

            #Cycle through filters
            for filter_item in filters.filter_array:
                #True list includes words to match
                true_list = filter_item['keywords']

                #Set false list to empty if there's no key
                false_list = []
                if "exclude" in filter_item:
                    false_list = filter_item['exclude']

                #If it matches any of the keywords and none of the exclude words, it will be matched
                if any(x in charge_text for x in true_list) and not any(x in charge_text for x in false_list):
                    crime_type = filter_item['category']
                    point_color = filter_item['color']

            row['crime'] = crime_type
            row['color'] = point_color

            #Finally, append row to array we're going to write out
            last_week.append(row)

    #Return array of results
    return last_week

#Renders the template
@application.route('/', methods=['GET'])
@application.route('/index/', methods=['GET'])
def index():                
    return render_template('index.html')

@application.route('/fetch/', methods=['POST'])
def fetch():
    print "fetch"



    content = {"sample": "hi"}
    r = jsonify(content)
    r.status_code = 200
    return r

@application.route('/process/', methods=['POST'])
def process():
    print "process"

@application.route('/map/<live>', methods=['POST'])
def map(live):
    print "map"


if __name__ == '__main__':
    application.run(host='0.0.0.0')
