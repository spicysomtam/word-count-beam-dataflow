package com.example;

import com.google.api.client.googleapis.auth.oauth2.GoogleCredential;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.http.HttpTransport;
import com.google.api.client.json.JsonFactory;
import com.google.api.client.json.jackson2.JacksonFactory;
import com.google.api.services.dataflow.Dataflow;
import com.google.api.services.dataflow.model.LaunchTemplateParameters;
//import com.google.api.services.dataflow.model.RuntimeEnvironment;
import com.google.cloud.functions.HttpFunction;
import com.google.cloud.functions.HttpRequest;
import com.google.cloud.functions.HttpResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.io.BufferedWriter;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

public class Example implements HttpFunction {
  @Override
  public void service(HttpRequest request, HttpResponse response) throws Exception {
                    Logger Log = LoggerFactory.getLogger(this.getClass());
        BufferedWriter writer = response.getWriter();
        try {
            writer.write("1");
            HttpTransport httpTransport = GoogleNetHttpTransport.newTrustedTransport();
            JsonFactory jsonFactory = JacksonFactory.getDefaultInstance();
            GoogleCredential credential = GoogleCredential.getApplicationDefault(httpTransport, jsonFactory);
            writer.write("2");
           
            // The createScopedRequired method returns true when running on GAE or a local developer
            // machine. In that case, the desired scopes must be passed in manually. When the code is
            // running in GCE, GKE or a Managed VM, the scopes are pulled from the GCE metadata server.
            // See https://developers.google.com/identity/protocols/application-default-credentials for more information.
            if (credential.createScopedRequired()) {
                credential = credential.createScoped(Collections.singletonList("https://www.googleapis.com/auth/cloud-platform"));
            }
            writer.write("3");
            Dataflow dataflowService = new Dataflow.Builder(httpTransport, jsonFactory, credential)
                    .setApplicationName("Google Cloud Platform Sample")
                    .build();

            // Add your code to assign values to parameters for the 'create' method:
            // * The project which owns the job.
            String projectId = "annular-haven-312209";

            // These setting depricated:
            //RuntimeEnvironment runtimeEnvironment = new RuntimeEnvironment();
            //runtimeEnvironment.setBypassTempDirValidation(false);
            //runtimeEnvironment.setTempLocation("gs://spicysomtam-dataflow-data-0/tmp");

            LaunchTemplateParameters launchTemplateParameters = new LaunchTemplateParameters();
            //launchTemplateParameters.setEnvironment(runtimeEnvironment);
            launchTemplateParameters.setJobName("word-count" + (new Date()).getTime());
            Map<String, String> params = new HashMap<String, String>();
            params.put("inputFile", "gs://spicysomtam-dataflow-data-0/inputFile/*.txt");
            params.put("output", "gs://spicysomtam-dataflow-data-0/outputFiles/output");
            params.put("tempLocation", "gs://spicysomtam-dataflow-data-0/tmp");
            launchTemplateParameters.setParameters(params);
            writer.write("4");
           
            Dataflow.Projects.Templates.Launch launch = dataflowService.projects().templates().launch(projectId, launchTemplateParameters);
            
            launch.setGcsPath("gs://spicysomtam-dataflow-templates/dataflow/templates/WordCount.json");
            launch.execute();
            
        }catch(Exception e){
            writer.write(e.toString());
        }
  }
}