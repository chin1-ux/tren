import subprocess
import os

env_vars = {
    "GEMINI_API_KEY": "AQ.Ab8RN6Irt3ijQNZubQi3MKMzpijhfWJ0SzV0aEl2NQ5wVMo_Yg",
    "SUPABASE_URL": "https://tdisqfmtvuljfstncxqv.supabase.co",
    "SUPABASE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRkaXNxZm10dnVsamZzdG5jeHF2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEzNjkxMzUsImV4cCI6MjA5Njk0NTEzNX0.roV1Z9MaUb4pV3Vw3IPA5kqKZLkr7aTfOhEDgcrXihk",
    "APIFY_API_TOKEN": "apify_api_9wMlDZ5eLbbVGndpCRR3a8GOgNfP1D1fr3m5",
    "YOUTUBE_API_KEY": "AIzaSyBUjnanYoZprB87rEZMy0cbIvZGagcV7ys",
    "RESEND_API_KEY": "re_9pu4Ljsq_8RdJXJ2zjJP6q28AquNmYYF6",
    "RESEND_FROM_EMAIL": "alerts@trendrop.ai",
    "SUPABASE_DB_URL": "postgresql://postgres.tdisqfmtvuljfstncxqv:nagaiah.rathna76@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres",
    "GROQ_API_KEY": "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,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",
    "SUPABASE_SERVICE_ROLE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRkaXNxZm10dnVsamZzdG5jeHF2Iiwicm9sZSI6InNlcnZlX3JvbGUiLCJpYXQiOjE3ODEzNjkxMzUsImV4cCI6MjA5Njk0NTEzNX0.KfUVkAJMGLf-ELlhWGGkcCuIdDd4AAL37_eiefGqst0"
}

# Delete existing ones to avoid conflicts
for name in env_vars.keys():
    print(f"Removing existing {name}...")
    subprocess.run("vercel env rm " + name + " production -y", shell=True, capture_output=True)

# Add cleanly
for name, value in env_vars.items():
    print(f"Adding {name}...")
    clean_val = value.strip()
    proc = subprocess.Popen(
        "vercel env add " + name + " production",
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=clean_val)
    print(stdout)
    if stderr:
        print("Error:", stderr)

print("Done pushing environment variables!")
