import subprocess
#from pprint import pprint

def run_pipeline():
  # java run time installed in ./jre folder which will be packaged into the zip file uploaded to the cloud function.
  # The zip file needs to include the java jar.
  cmd = "./jre/bin/java -cp ./target/dataflow-intro-bundled-0.1.jar com.example.WordCount "
  cmd += "--runner=DataflowRunner "
  cmd += "--project=annular-haven-312209 "
  cmd += "--region=europe-west2 "
  cmd += "--tempLocation=gs://spicysomtam-dataflow-0/tmp/ "
  cmd += "--inputFile=gs://spicysomtam-dataflow-data-0/inputFiles/*.txt "
  cmd += "--output=gs://spicysomtam-dataflow-data-0/outputFiles/output "
  pprint(cmd)
  r = subprocess.run(cmd, shell=True) 

  return r

if __name__ == "__main__":
   r = run_pipeline()
   #pprint(r)
   exit(r.returncode)
