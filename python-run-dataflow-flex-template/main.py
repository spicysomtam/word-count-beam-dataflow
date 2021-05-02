from googleapiclient.discovery import build
import google.auth
import os
import json
import datetime
from pprint import pprint

# This does not work in latest cloud functions:
#def get_project_id():
#  # If this is running in a cloud function, then GCP_PROJECT should be defined
#  if 'GCP_PROJECT' in os.environ:
#    p = os.environ['GCP_PROJECT']
#  # else if this is running locally then GOOGLE_APPLICATION_CREDENTIALS should be defined
#  elif 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
#    with open(os.environ['GOOGLE_APPLICATION_CREDENTIALS'], 'r') as fp:
#      c = json.load(fp)
#    p = c['project_id']
#
#  return p

# We are not using flask/http with this so instead request is just a dict
def run_dataflow(event,context):
  credentials, _ = google.auth.default()

  # cache_discovery should be set to False to avoid errors
  dataflow = build('dataflow', 'v1b3', credentials = credentials, cache_discovery=False)

  #projectId = get_project_id()
  projectId = 'annular-haven-312209'

  gsd = 'gs://spicysomtam-dataflow-data-0'
  gst = 'gs://spicysomtam-dataflow-templates'

  request = dataflow.projects().locations().flexTemplates().launch(
    location = 'us-central1',
    projectId = projectId,
    body = {
      'launch_parameter': {
        'jobName': 'word-count-'+datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
        'parameters': {
          'inputFile': gsd+'/inputFiles/*.txt',
          'output': gsd+'/outputFiles/output',
          'tempLocation': gsd+'/tmp/'
        },
        'containerSpecGcsPath': gst+'/dataflow/templates/WordCount.json'
      }
    }
  )

  # submit the job
  response = request.execute()
  return response
  #return 0

# Local development
if __name__ == '__main__':
  result = run_dataflow('x','y')
  print(result)
