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
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/dataflow-0.json
```

# Run with maven and service account

Need env var GOOGLE_APPLICATION_CREDENTIALS setting up as earlier. Then run with maven:
```
cd dataflow-intro
mvn compile exec:java \
  -Dexec.mainClass=com.example.WordCount \
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

# Switch to an inputFile and a seperate bucket for data

This time we want to specify the inputFile, and keep the dataflow data and input and output data seperate using a data bucket.

Create the additional bucket:

```
gsutil mb gs://some-name-dataflow-data-0
```

Test re-run using a different output:
```
java -cp target/dataflow-intro-bundled-0.1.jar com.example.WordCount \
  --runner=DataflowRunner \
  --project=some-name-312209 \
  --region=europe-west2 \
  --tempLocation=gs://some-name-dataflow-0/tmp/ \
  --output=gs://some-name-dataflow-data-0/outputFiles/output
```

Still working? Continue on to preparing an inputFile:
```
gsutil cp gs://apache-beam-samples/shakespeare/kinglear.txt gs://some-name-dataflow-data-0/inputFiles/
```

Rerun using inputFile:
```
java -cp target/dataflow-intro-bundled-0.1.jar com.example.WordCount \
  --runner=DataflowRunner \
  --project=some-name-312209 \
  --region=europe-west2 \
  --tempLocation=gs://some-name-dataflow-0/tmp/ \
  --inputFile=gs://some-name-dataflow-data-0/inputFiles/*.txt \
  --output=gs://some-name-dataflow-data-0/outputFiles/output
```

# Triggering a run of a dataflow pipeline

We have discussed how to run a pipeline via Maven (development scenario) and Java (real run). I would like to trigger a pipeline in Google cloud with minimum resources or infrastructure; Cloud Functions seems ideal for this as they can triggered in many ways. Thus I believe we have several options:
* A Java Cloud Function that contains the pipeline jar, which runs java as per examples above.
* A Dataflow template where the jar (or java classes) have been staged on some storage; this is perferable as its smaller than a Cloud function that contains a jar and probably quicker to run as there is no need to upload a fat jar, etc. This [Google blog page](https://www.googlenewsapp.com/turn-any-dataflow-pipeline-into-a-reusable-template/) explains in detail how it works, and also describes the two types of Dataflow templates available:
* Classic templates
* Flex templates

Lets try and create these templates and use them.

Lets cleanup our dataflow bucket before continuing:
```
gsutil -m rm gs://some-name-dataflow-0/*
```

## Dataflow classic template

This involves making code changes to change the input parameters and such to ones that can be passed at execution time. Its kind of a fudge and we are recommended to use Flex templates instead.

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
  -Dexec.args="--project=some-name-312209 \
  --runner=DataflowRunner \
  --stagingLocation=gs://some-name-dataflow-0/staging \
  --templateLocation=gs://some-name-dataflow-0/templates/WordCount \
  --region=europe-west2" \
  -Pdataflow-runner
```

Code fails to build:
```
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.7.0:compile (default-compile) on project dataflow-intro-classic-template: Compilation failure
[ERROR] /media/data/amunro-git/some-name/word-count-beam-dataflow/dataflow-intro-classic-template/src/main/java/com/example/WindowedWordCount.java:[175,44] incompatible types: org.apache.beam.sdk.options.ValueProvider<java.lang.String> cannot be converted to java.lang.String
```

Google docs clearly need updating as the `getOutput` part of the code is not in their docs.

I give up on this and move onto Flex Templates. You are welcome to check this out again, follow instructions, and get it working.

# Flex templates

This is documented in official Google cloud [documentation](https://cloud.google.com/dataflow/docs/guides/templates/using-flex-templates).

Also refer to the [Configuring Flex Templates Documentation](https://cloud.google.com/dataflow/docs/guides/templates/configuring-flex-templates).

In essence it uses a docker image, to which we add the jar.

Lets cut the instructions down and re-use what we have already setup.

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
export TEMPLATE_PATH="gs://some-name-dataflow-0/dataflow/templates/WordCount.json"
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/dataflow-0.json
```

Create a `metadata.json` file; here is a sample:
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

In the gui you can run a job from this template by selecting Create Job From Template, then custom template, and the gs:// location of the template (TEMPLATE_PATH env var above).

Running the flex template as a Dataflow job:
```
gcloud dataflow flex-template run "word-count-`date +%Y%m%d-%H%M%S`" \
    --template-file-gcs-location "$TEMPLATE_PATH" \
    --parameters inputFile="gs://some-name-dataflow-data-0/inputFiles/*.txt",output="gs://some-name-dataflow-data-0/outputFiles/output",,tempLocation="gs://some-name-dataflow-0/tmp/" \
    --region=europe-west2
```

Oddly, jobs are queued when run from a template, rather than straight away; need to investigate why this is.

# Cleanup

Remove the Google Cloud buckets:
```
gsutil rm -r gs://some-name-dataflow-0
gsutil rm -r gs://some-name-dataflow-data-0
```