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
project = annular-haven-312209

Your active configuration is: [default]

```

I then setup a default region to match where I am going to run it:
```
gcloud compute project-info describe --project annular-haven-312209
gcloud compute project-info add-metadata --metadata google-compute-default-region=europe-west2,google-compute-default-zone=europe-west2-b
gcloud compute project-info describe --project annular-haven-312209
```

Docs for this are [here](https://cloud.google.com/compute/docs/regions-zones/changing-default-zone-region#gcloud).

# Create a google bucket

We need a bucket to pass the code to run to dataflow, to pass any data we want dataflow to process, and finally for dataflow to return results. Lets create a bucket:
```
gsutil mb gs://spicysomtam-dataflow-0
```

# Need service account to run the job

I was getting this issue:
```
Unable to get application default credentials. Please see https://developers.google.com/accounts/docs/application-default-credentials for details on how to specify credentials. This version of the SDK is dependent on the gcloud core component version 2015.02.05 or newer to be able to get credentials from the currently authorized user via gcloud auth.
```

Following the link I need a service account; not sure this is the best way, but it works:
```
gcloud auth login # Choose your gmail account to auth with gcloud
gcloud iam service-accounts create dataflow-0
gcloud config list
gcloud projects add-iam-policy-binding annular-haven-312209 --member="serviceAccount:dataflow-0@annular-haven-312209.iam.gserviceaccount.com" --role="roles/owner"
```

Docs for [this](https://cloud.google.com/dataflow/docs/concepts/security-and-permissions).

I tried the arg `serviceAccount=dataflow-0@annular-haven-312209.iam.gserviceaccount.com`, but that did not work.

Setup the key file and env var:
```
gcloud iam service-accounts keys create dataflow-0.json --iam-account=dataflow-0@annular-haven-312209.iam.gserviceaccount.com
cd dataflow-intro
cat dataflow-0.json
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/dataflow-0.json
```

# Run with maven and service account

Need env var GOOGLE_APPLICATION_CREDENTIALS setting up as earlier. Then run with maven:
```
cd dataflow-intro
mvn compile exec:java \
  -Dexec.mainClass=com.example.WordCount \
  -Dexec.args="--project=annular-haven-312209 \
  --gcpTempLocation=gs://spicysomtam-dataflow-0/tmp/ \
  --output=gs://spicysomtam-dataflow-0/output \
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
  --project=annular-haven-312209 \
  --region=europe-west2 \
  --tempLocation=gs://spicysomtam-dataflow-0/tmp/ \
  --output=gs://spicysomtam-dataflow-0/output
```

# Switch to an inputFile and a seperate bucket for data

This time we want to specify the inputFile, and keep the dataflow input and output data seperate from dataflow tmp using a data bucket. The logic here is the data bucket is consumed by something else and I don't want that having access to the inner workings of the dataflow process.

Create the additional bucket:

```
gsutil mb gs://spicysomtam-dataflow-data-0
```

Test re-run using a different output:
```
java -cp target/dataflow-intro-bundled-0.1.jar com.example.WordCount \
  --runner=DataflowRunner \
  --project=annular-haven-312209 \
  --region=europe-west2 \
  --tempLocation=gs://spicysomtam-dataflow-0/tmp/ \
  --output=gs://spicysomtam-dataflow-data-0/outputFiles/output
```

Still working? Continue on to preparing an inputFile:
```
gsutil cp gs://apache-beam-samples/shakespeare/kinglear.txt gs://spicysomtam-dataflow-data-0/inputFiles/
```

Rerun using inputFile:
```
java -cp target/dataflow-intro-bundled-0.1.jar com.example.WordCount \
  --runner=DataflowRunner \
  --project=annular-haven-312209 \
  --region=europe-west2 \
  --tempLocation=gs://spicysomtam-dataflow-0/tmp/ \
  --inputFile=gs://spicysomtam-dataflow-data-0/inputFiles/*.txt \
  --output=gs://spicysomtam-dataflow-data-0/outputFiles/output
```

# Triggering a run of a dataflow pipeline

We have discussed how to run a pipeline via Maven (development scenario) and Java (real run). I would like to trigger a pipeline in Google cloud with minimum resources or infrastructure; Cloud Functions seems ideal for this as they can triggered in many ways. Thus I believe we have several options:
* A Java Cloud Function that contains the pipeline jar, which runs java as per examples above. This is the only way to upload a jar; note this is to encourage the use of templates; see next section.
* A Dataflow template where the jar (or java classes) have been staged on some storage; this is perferable as its smaller than a Cloud Function that contains a jar and probably quicker to run as there is no need to upload a fat jar, etc on each invocation. This [Google blog page](https://www.googlenewsapp.com/turn-any-dataflow-pipeline-into-a-reusable-template/) explains in detail how it works, and also describes the two types of Dataflow templates available:
  * Classic templates
  * Flex templates

Lets try and create these templates and use them.

Lets cleanup our dataflow bucket before continuing:
```
gsutil -m rm gs://spicysomtam-dataflow-0/*
```

## Cloud function with embeded jar and java

This is considered the old and least elegant way, but is probably the simplest. This implies you either use a Java based Cloud Function or one which has Java installed via the zip file option. Note that Java is not particular cloud or container friendly and does not have the simplicity and ease of execution that more modern languages have. Thus the use of Java may not be the easiest solution (unless Java is your thing), and if you wish to go this way, you would probably be best to use say Python (or Node.js), and shell out to run Java via a mini jre installed in the Cloud Function zip file. 

I did not want to spent too much time on setting up and testing this solution as its unlikely to be the best solution to implement; thus I have just included a Python script  in the `python-execute-java-to-run-dataflow` folder that gives you an example of how to shell out to run Java. 


## Dataflow classic template

This involves making code changes to change the input parameters to ones that can be passed at execution time. Its kind of a fudge and may not work out well if your pipeline flow may change as a result of different inputs. Thus Google recommended to use Flex templates instead and classic templates are only there for backward compatibility.

Thus we try and generate a wordcount example, and follow [official documentation](https://cloud.google.com/dataflow/docs/guides/templates/creating-templates) to modify the code:

```
mvn archetype:generate \
  -DarchetypeGroupId=org.apache.beam \
  -DarchetypeArtifactId=beam-sdks-java-maven-archetypes-examples \
  -DgroupId=com.example \
  -DartifactId=dataflow-intro-classic-template \
  -Dversion="0.1" \
  -DinteractiveMode=false \
  -Dpackage=com.example
```

Then create the Dataflow template following Google docs:
```
cd dataflow-intro-classic-template
mvn compile exec:java \
  -Dexec.mainClass=com.example.WordCount \
  -Dexec.args="--project=annular-haven-312209 \
  --runner=DataflowRunner \
  --stagingLocation=gs://spicysomtam-dataflow-0/staging \
  --templateLocation=gs://spicysomtam-dataflow-0/templates/WordCount \
  --region=europe-west2" \
  -Pdataflow-runner
```

Code fails to build:
```
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.7.0:compile (default-compile) on project dataflow-intro-classic-template: Compilation failure
[ERROR] /media/data/amunro-git/spicysomtam/word-count-beam-dataflow/dataflow-intro-classic-template/src/main/java/com/example/WindowedWordCount.java:[175,44] incompatible types: org.apache.beam.sdk.options.ValueProvider<java.lang.String> cannot be converted to java.lang.String
```

Google docs clearly need updating as the `getOutput` part of the code is not in their docs.

I gave up on this and moved onto Flex Templates. You are welcome to check this out again, follow instructions, and get it working.

## Dataflow flex template

This is documented in official Google cloud [documentation](https://cloud.google.com/dataflow/docs/guides/templates/using-flex-templates).

Also refer to the [Configuring Flex Templates Documentation](https://cloud.google.com/dataflow/docs/guides/templates/configuring-flex-templates).

In essence it uses a docker image, to which we add the jar.

Pros:
* Highly configurable; eg you can specify the gcp instance type, number of instances, etc, and thus scale the dataflow runs to meet your needs.
* Don't need to upload jar file to dataflow on each invokation (or store jar on executor for upload).

Cons:
* Slow to start dataflow job; job shows as queued on startup rather than going straight to running state.
* Complex configuration of template (more about about this below).

### Creating the template

Lets cut the [official instructions](https://cloud.google.com/dataflow/docs/guides/templates/using-flex-templates) down and re-use what we have already setup.

The main class for your beam app will need a slight tweak (don't forget to repackage your jar):
```
   // For a Dataflow Flex Template, do NOT waitUntilFinish().
    //p.run().waitUntilFinish();
    p.run();
```

In your Linux shell, setup some env vars:
```
export PROJECT="$(gcloud config get-value project)"
export TEMPLATE_IMAGE="gcr.io/$PROJECT/dataflow/templates/word-count:latest"
export TEMPLATE_PATH="gs://spicysomtam-dataflow-0/dataflow/templates/WordCount.json"
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/dataflow-0.json
```

Create a `metadata.json` file for the parameters; here is a sample:
```
{
  "name": "Apache Beam WordCount",
  "description": "An Apache Beam WordCount example",
  "parameters": [
    {
      "name": "inputFile",
      "label": "Input files",
      "helpText": "Input file/s to process on a google storage bucket.",
      "isOptional": true,
      "regexes": [
        "^gs:\/\/.+$"
      ]
    },
    {
      "name": "output",
      "label": "output file pattern",
      "helpText": "Output file spec pattern on a google storage bucket",
      "regexes": [
        "^gs:\/\/.+$"
      ]
    },
    {
      "name": "tempLocation",
      "label": "temporary work location",
      "helpText": "Temporary work location on a google storage bucket",
      "regexes": [
        "^gs:\/\/.+$"
      ]
    }
  ]
}
```

Ensure the Container Registry APIs are enabled for your gcp project; instructions [here](https://cloud.google.com/container-registry/docs/quickstart).

Creating the Flex template (in the root dir of this repo):
```
gcloud dataflow flex-template build $TEMPLATE_PATH \
      --image-gcr-path "$TEMPLATE_IMAGE" \
      --sdk-language "JAVA" \
      --flex-template-base-image JAVA11 \
      --metadata-file "metadata.json" \
      --jar "dataflow-intro/target/dataflow-intro-bundled-0.1.jar" \
      --env FLEX_TEMPLATE_JAVA_MAIN_CLASS="com.example.WordCount"
```

This will create a TEMPLATE_PATH file on a Google storage bucket and a docker image in Google Container Registry in you GCP project.

### Running the job via a flex template from the console

In the gui you can run a job from this template by selecting Create Job From Template, then custom template, and the `gs://<bucket>/<file-spec>` location of the template (TEMPLATE_PATH env var abovei; eg `gs://spicysomtam-dataflow-0/dataflow/templates/WordCount.json`).

### Running the job via a flex template using the gcloud command line

Running the flex template as a Dataflow job:
```
gcloud dataflow flex-template run "word-count-`date +%Y%m%d-%H%M%S`" \
    --template-file-gcs-location "gs://spicysomtam-dataflow-0/dataflow/templates/WordCount.json" \
    --parameters inputFile="gs://spicysomtam-dataflow-data-0/inputFiles/*.txt",output="gs://spicysomtam-dataflow-data-0/outputFiles/output",tempLocation="gs://spicysomtam-dataflow-0/tmp/" \
    --region=europe-west2
```

Jobs are queued when run from a template, rather than straight away; this is due to the need to spin up the docker image created by template creation, etc.

### Running the job via a flex template using a Cloud Function

Here we move on to using a Cloud Function to execute the dataflow job using a dataflow flex template. Why would we want to do this? Because Cloud Functions are the serverless Google Cloud way to run code via many triggers. Serverless means we do not need to deploy any infrastructure or networking to run compute.

I used Python as am more familiar with that then Node.js. 

Also I found a Java 11 example which I have included (see below).

#### Get setup for local development on your pc

There are two choices here:
* Use gcloud, setup your credentials, authentication, etc, and develop locally as normal.
* Use the google functional-framework, which will allow you to develop locally as if you were developing a Cloud Function on the GCP console. I did not try this
although you can follow instructions at the [getting started guide](https://cloud.google.com/functions/docs/functions-framework). 

#### Develop locally with python

I won't go into gcloud cli setup; follow [GCP docs[(https://cloud.google.com/sdk/docs/install)] for this! You will also need to authenticate against your Google Cloud account: `gcloud auth login`.

#### Basic Cloud Function

Sample code is in the `python-run-dataflow-flex-template` folder; change directory there.

Some `pip` setup; I used `python3.8` on ubuntu 20.04 using `pip3` (`pip` is for python 2); you should check what versions are available in the GCP Cloud Functions and setup your local environment appropriatly. 

See the python dependancies required in `requirements.txt`.

We then need to use the Service Account defined earlier, and define the env variable for it.
 
Now we can just develop and run the scripts as follow:
```
python3 main.py
```

#### Creating the Cloud Flow function

I just used the gui, defining a Cloud Storage function using a Cloud Storage trigger (event Finalize/create). I called it `bucket_watcher`.

Sample code is in the `python-cloud-function-bucket-watcher`; cut and paste `main.py` into the cloud function.

Use the dependancies in the `requirements.txt` to setup the same file in the Cloud Function.

You can test by copying a text file of extension `.txt` (eg `a.txt`) to `gs://<bucket>/inputFiles/`:
```
gsutil cp a.txt gs://spicysomtam-dataflow-data-0/inputFiles/a.txt
```

Examine logging as follows (might take a couple of minutes to come through):
```
gcloud functions logs read
```

You will see something like this:
```
D      bucket-watcher  339nphkdt3nm  2021-05-04 18:37:52.545  Function execution took 1956 ms, finished with status: 'ok'
       bucket-watcher  339nphkdt3nm  2021-05-04 18:37:51.469  Creating dataflow job: word-count-20210504-183751.
       bucket-watcher  339nphkdt3nm  2021-05-04 18:37:50.600  Processing file: inputFiles/a.txt.
D      bucket-watcher  339nphkdt3nm  2021-05-04 18:37:50.591  Function execution started
```

#### Java 11 example

I found [this example](https://github.com/karthikeyan1127/Java_CloudFunction_DataFlow). I updated it with the settings for my example. 

Can deploy this as a Cloud Function:
* I used a http Cloud Function as the code is a http example.
* Code is in the `java-dataflow-flex-template` folder.
* Don't forget to include the `pom.xml`
* May need to size memory up to work with Java (I set to 1Gb to be sure).

This example uses the Dataflow 2.5.0 deplicated api; I updated the `pom.xml` for the newer settings, but it still does not work:
```
1234com.google.api.client.googleapis.json.GoogleJsonResponseException: 400 Bad Request
POST https://dataflow.googleapis.com/v1b3/projects/annular-haven-312209/templates:launch?gcsPath=gs://spicysomtam-dataflow-templates/dataflow/templates/WordCount.json
{
  "code" : 400,
  "errors" : [ {
    "domain" : "global",
    "message" : "(4f88cb4625e8e960): There is no support for job type  with environment version . Please try upgrading the SDK to the latest version. You can find the instructions on installing the latest SDK at https://cloud.google.com/dataflow/docs/guides/installing-beam-sdk. If that doesn't work, please contact the Cloud Dataflow team for assistance at https://cloud.google.com/dataflow/support.",
    "reason" : "badRequest"
  } ],
  "message" : "(4f88cb4625e8e960): There is no support for job type  with environment version . Please try upgrading the SDK to the latest version. You can find the instructions on installing the latest SDK at https://cloud.google.com/dataflow/docs/guides/installing-beam-sdk. If that doesn't work, please contact the Cloud Dataflow team for assistance at https://cloud.google.com/dataflow/support.",
  "status" : "INVALID_ARGUMENT"
}
```
Not sure what the answer is (Java isn't my thing); maybe Google thinks you should just use a newer programming language to run a submit?

### Cleanup of the template

* Delete the generated docker image.
* Delete the template json file (TEMPLATE_PATH env var, etc).

# Cleanup

Remove the Google Cloud buckets:
```
gsutil rm -r gs://spicysomtam-dataflow-0
gsutil rm -r gs://spicysomtam-dataflow-data-0
```