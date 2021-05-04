from googleapiclient.discovery import build
import google.auth
import os
import json
import datetime
from pprint import pprint
import re

def bucket_watcher(event,context):
  if re.search("^inputFiles\/.+.txt$",event['name']):
    r = run_dataflow(event['name'])

  return r


def run_dataflow(f):
  print(f"Processing file: {f}.")
  credentials, _ = google.auth.default()

  # cache_discovery should be set to False to avoid errors
  dataflow = build('dataflow', 'v1b3', credentials = credentials, cache_discovery=False)

  projectId = 'annular-haven-312209'

  gsd = 'gs://spicysomtam-dataflow-data-0'
  gst = 'gs://spicysomtam-dataflow-templates'

  jobName = 'word-count-'+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

  request = dataflow.projects().locations().flexTemplates().launch(
    location = 'us-central1',
    projectId = projectId,
    body = {
      'launch_parameter': {
        'jobName': jobName,
        'parameters': {
          'inputFile': gsd+'/'+f,
          'output': gsd+'/outputFiles/output',
          'tempLocation': gsd+'/tmp/'
        },
        'containerSpecGcsPath': gst+'/dataflow/templates/WordCount.json'
      }
    }
  )

  # submit the job
  print(f"Creating dataflow job: {jobName}.")
  response = request.execute()
  return response

if __name__ == "__main__":
   r = bucket_watcher({'name': 'inputFiles/a.txt'},None)
