import os
import hmac
import hashlib
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure APIs
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use Gemini 2.5 Flash for fast, cost-effective reasoning
model = genai.GenerativeModel('gemini-2.5-flash')

def verify_signature(payload_body, header_signature):
    """Secures the endpoint by verifying the request actually came from GitHub."""
    if not WEBHOOK_SECRET or not header_signature:
        return False
    
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected_signature, header_signature)

def get_pr_diff(repo_full_name, pr_number):
    """Fetches the actual code changes from the Pull Request."""
    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.diff"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    return None

def post_pr_comment(repo_full_name, pr_number, comment_body):
    """Posts the architectural review back to GitHub."""
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.post(url, headers=headers, json={"body": comment_body})
    print(f"👉 GITHUB API STATUS: {response.status_code}") # Yeh error batayega
    print(f"👉 GITHUB API RESPONSE: {response.text}") # Yeh exact reason batayega

def analyze_code_with_gemini(diff_text):
    """Sends the diff to Gemini to check for algorithmic inefficiencies."""
    prompt = f"""
    You are a Principal Software Engineer reviewing a Pull Request.
    Your only job is to find algorithmic inefficiencies (e.g., O(n^2) nested loops that could be O(n)).
    Analyze the following git diff and determine if there is a way to optimize the time or space complexity.
    
    Return ONLY a valid JSON object with the following schema:
    {{
        "has_inefficiency": boolean,
        "original_complexity": "string (e.g., O(n^2))",
        "optimized_complexity": "string (e.g., O(n log n))",
        "explanation": "string explaining why it is inefficient and how to fix it",
        "refactored_code": "string containing the improved code snippet"
    }}
    
    Code Diff:
    {diff_text}
    """
    
    try:
        # Enforcing JSON output to ensure the app doesn't crash on parsing
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {"has_inefficiency": False}

@app.route('/webhook', methods=['POST'])
def github_webhook():
    # 1. Verify Security Signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Unauthorized"}), 401

    event = request.headers.get('X-GitHub-Event')
    
    # 2. Only process Pull Requests
    if event == "pull_request":
        payload = request.json
        action = payload.get("action")
        
        if action in ["opened", "synchronize"]:
            repo_name = payload["repository"]["full_name"]
            pr_number = payload["pull_request"]["number"]
            
            # 3. Fetch the code changes
            diff = get_pr_diff(repo_name, pr_number)
            if not diff:
                return jsonify({"error": "Could not fetch diff"}), 400
                
            # 4. Analyze with Agent
            analysis = analyze_code_with_gemini(diff)
            print(f"👉 GEMINI ANALYSIS RESULT: {analysis}")
            
            # 5. Take Action if inefficient
            if analysis.get("has_inefficiency"):
                markdown_comment = (
                    f"### ⚠️ Agentic Code Review: Algorithmic Optimization Detected\n\n"
                    f"**Current Complexity:** `{analysis['original_complexity']}`\n"
                    f"**Target Complexity:** `{analysis['optimized_complexity']}`\n\n"
                    f"**Architectural Analysis:**\n{analysis['explanation']}\n\n"
                    f"**Suggested Refactor:**\n```python\n{analysis['refactored_code']}\n```"
                )
                post_pr_comment(repo_name, pr_number, markdown_comment)
                return jsonify({"status": "Review posted"}), 200
            
            return jsonify({"status": "Code looks optimal, no action taken"}), 200

    return jsonify({"status": "Event ignored"}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)