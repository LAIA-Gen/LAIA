import subprocess
import time

def call_flutter_code_gen(app_name: str):
    subprocess.run("flutter clean", cwd=f"./{app_name}", shell=True)
    time.sleep(5)
    subprocess.run(["flutter", "pub", "run", "build_runner", "build"], cwd=f"./{app_name}", shell=True)
    time.sleep(5)
    subprocess.Popen("flutter run -d chrome", cwd=f"./{app_name}", shell=True)
