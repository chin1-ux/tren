import subprocess
import json
import time
import sys

target_sha = "8c2cbfb"
print(f"Waiting for Vercel preview deployment for commit {target_sha}...")

for attempt in range(1, 30):
    cmd = ['gh', 'api', 'repos/ch1n-may/trendrop/deployments?per_page=10']
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        try:
            data = json.loads(res.stdout)
            for d in data:
                sha = d.get('sha', '')
                if sha.startswith(target_sha):
                    did = d.get('id')
                    env = d.get('environment')
                    # check status
                    st_cmd = ['gh', 'api', f'repos/ch1n-may/trendrop/deployments/{did}/statuses']
                    st_res = subprocess.run(st_cmd, capture_output=True, text=True)
                    if st_res.returncode == 0:
                        st_data = json.loads(st_res.stdout)
                        if st_data:
                            latest_st = st_data[0]
                            state = latest_st.get('state')
                            url = latest_st.get('environment_url') or latest_st.get('target_url')
                            print(f"Attempt {attempt}: Deployment {did} found for {target_sha}: state={state}, url={url}")
                            if state == 'success':
                                print(f"SUCCESS: Preview URL is {url}")
                                sys.exit(0)
                            elif state == 'failure' or state == 'error':
                                print(f"FAILED: Deployment failed: {latest_st.get('description')}")
                                sys.exit(1)
        except Exception as e:
            print(f"Parse error: {e}")
    else:
        print(f"gh api error: {res.stderr}")
    time.sleep(5)

print("Timed out waiting for preview deployment.")
sys.exit(2)
