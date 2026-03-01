import os
import hmac
import hashlib
import json
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Using Gemini 2.5 Flash as requested for real-world fast execution
model = genai.GenerativeModel('gemini-2.5-flash')

def verify_signature(payload_body, header_signature):
    if not WEBHOOK_SECRET or not header_signature:
        return False
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), header_signature)

def get_pr_diff(repo_full_name, pr_number):
    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3.diff"}
    response = requests.get(url, headers=headers)
    return response.text if response.status_code == 200 else None

def post_pr_comment(repo_full_name, pr_number, comment_body):
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.post(url, headers=headers, json={"body": comment_body})
    print(f"👉 GITHUB POST STATUS: {response.status_code}") # Debugging Tracker
    print(f"👉 GITHUB RESPONSE: {response.text}")

def analyze_code_with_gemini(diff_text):
    prompt = f"""
    You are a Principal Software Engineer. Analyze this git diff for algorithmic inefficiencies.
    Return ONLY a valid JSON object:
    {{
        "has_inefficiency": boolean,
        "original_complexity": "string",
        "optimized_complexity": "string",
        "explanation": "string",
        "refactored_code": "string"
    }}
    Diff: {diff_text}
    """
    try:
        start_time = time.time()
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result = json.loads(response.text)
        result["latency"] = round(time.time() - start_time, 2)
        print(f"👉 GEMINI DETECTED INEFFICIENCY: {result.get('has_inefficiency')}") # Debugging Tracker
        return result
    except Exception as e:
        print(f"👉 GEMINI ERROR: {e}")
        return {"has_inefficiency": False}

@app.route('/webhook', methods=['POST'])
def github_webhook():
    print("\n🚀 --- WEBHOOK TRIGGERED ---")
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        print("❌ SECURITY FAILED: Signature mismatch")
        return jsonify({"error": "Unauthorized"}), 401

    event = request.headers.get('X-GitHub-Event')
    print(f"📥 EVENT RECEIVED: {event}")
    
    if event == "pull_request":
        payload = request.json
        action = payload.get("action")
        print(f"🔧 ACTION: {action}")
        
        if action in ["opened", "synchronize", "reopened"]:
            repo_name = payload["repository"]["full_name"]
            pr_number = payload["pull_request"]["number"]
            
            diff = get_pr_diff(repo_name, pr_number)
            if diff:
                analysis = analyze_code_with_gemini(diff)
                if analysis.get("has_inefficiency"):
                    comment = (
                        f"### ⚡ Agentic Code Review\n"
                        f"**Time Complexity Improvement:** `{analysis['original_complexity']}` ➡️ `{analysis['optimized_complexity']}`\n\n"
                        f"**Analysis:** {analysis['explanation']}\n\n"
                        f"**Refactor:**\n```python\n{analysis['refactored_code']}\n```\n"
                        f"> *Latency: {analysis.get('latency')}s | Model: gemini-2.5-flash*"
                    )
                    post_pr_comment(repo_name, pr_number, comment)
                    return jsonify({"status": "Review posted"}), 200
                else:
                    print("✅ CODE IS OPTIMAL. No comment needed.")
            else:
                print("❌ ERROR: Could not fetch Diff.")
    return jsonify({"status": "Processed"}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)