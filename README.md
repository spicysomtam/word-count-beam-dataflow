# Introduction

This is a proof of concept deploying Apache Beam word-count example using the Dataflow running in Google Cloud.

I was attempting to get it running outside the google cloud Active Cloud Shell (built in shell).

I used Ubuntu 20.04 openJDK 1.8 (should be good with Oracle Java 1.8/1.11 OpenJDK 11, etc). 

# Generating the code

This is a cut and paste of the Java Dataflow example within the Google Cloud Console:

```
mvn archetype:generate     \
  -DarchetypeGroupId=org.apache.beam \
  -DarchetypeArtifactId=beam-sdks-java-maven-archetypes-examples \
  -DgroupId=com.example \
  -DartifactId=dataflow-intro \
  -Dversion="0.1" \
  -DinteractiveMode=false \
  -Dpackage=com.example
```

It will generate the content in the `dataflow-intro` directory (which I included in this repo).

# Google account setup

You need to install `gcloud` via your OS installer, and get yourself a google cloud account setup.

My config looks similar to this:
```
$ gcloud config list
[core]
account = XXXX@gmail.com
disable_usage_reporting = True
project = some-name-312209

Your active configuration is: [default]

```

I then setup a default region to match where I am going to run it:
```
gcloud compute project-info describe --project some-project-312209
gcloud compute project-info add-metadata --metadata google-compute-default-region=europe-west2,google-compute-default-zone=europe-west2-b
gcloud compute project-info describe --project some-project-312209
```

Docs for this are [here](https://cloud.google.com/compute/docs/regions-zones/changing-default-zone-region#gcloud).

# Create a google bucket

We need a bucket to pass the code to run to dataflow, to pass any data we want dataflow to process, and finally for dataflow to return results. Lets create a bucket:
```
gsutil mb gs://some-name-dataflow-0
```

# Need service account to run the job

I was getting this issue:
```
Unable to get application default credentials. Please see https://developers.google.com/accounts/docs/application-default-credentials for details on how to specify credentials. This version of the SDK is dependent on the gcloud core component version 2015.02.05 or newer to be able to get credentials from the currently authorized user via gcloud auth.
```

Following the link I need a service account; not sure this is the best way, but it works:
```
gcloud iam service-accounts create dataflow-0
gcloud config list
gcloud projects add-iam-policy-binding some-name-312209 --member="serviceAccount:dataflow-0@some-name-312209.iam.gserviceaccount.com" --role="roles/owner"
```

Docs for [this](https://cloud.google.com/dataflow/docs/concepts/security-and-permissions).

I tried the arg `serviceAccount=dataflow-0@some-name-312209.iam.gserviceaccount.com`, but that did not work.

Setup the key file and env var:
```
gcloud iam service-accounts keys create dataflow-0.json --iam-account=dataflow-0@some-name-312209.iam.gserviceaccount.com
cd dataflow-intro
cat dataflow-0.json
export GOOGLE_APPLICATION_CREDENTIALS="dataflow-0.json"
```

# Run with maven and service account

Need env var GOOGLE_APPLICATION_CREDENTIALS setting up as earlier. Then run with maven:
```
cd dataflow-intro
mvn compile exec:java -Dexec.mainClass=com.example.WordCount \
  -Dexec.args="--project=some-name-312209 \
  --gcpTempLocation=gs://some-name-dataflow-0/tmp/ \
  --output=gs://some-name-dataflow-0/output \
  --runner=DataflowRunner \
  --jobName=dataflow-intro \
  --region=europe-west2" \
  -Pdataflow-runner
```

# Run with java and service account

Package the jar:
```
cd dataflow-intro
mvn package -Pdataflow-runner -DskipTests
```

Then run with java (need env var GOOGLE_APPLICATION_CREDENTIALS setting up as earlier). 
```
java -cp target/dataflow-intro-bundled-0.1.jar com.example.WordCount \
  --runner=DataflowRunner \
  --project=some-name-312209 \
  --region=europe-west2 \
  --tempLocation=gs://some-name-dataflow-0/tmp/ \
  --output=gs://some-name-dataflow-0/output
```

# Cleanup

Remove the Google Cloud bucket:
```
gsutil rm -r gs://some-name-dataflow-0
```