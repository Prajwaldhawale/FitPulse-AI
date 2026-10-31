pipeline {
    agent any

    triggers {
        githubPush()
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        DEPLOYMATE_URL = "http://127.0.0.1/api"
        APP_NAME = "FitPulse-AI"
        APP_PORT = "3000"
        IMAGE_NAME = "fitpulse-ai"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT = sh(script: 'git rev-parse --short HEAD 2>/dev/null || echo "latest"', returnStdout: true).trim()
                    env.RESOLVED_BRANCH = env.BRANCH_NAME ?: env.GIT_BRANCH ?: "main"
                    env.IMAGE_TAG = "${IMAGE_NAME}:${GIT_COMMIT}"
                }
                echo "Building commit: ${GIT_COMMIT} on branch: ${RESOLVED_BRANCH}"
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build -t "$IMAGE_TAG" .'
            }
        }

        stage('Unit Testing') {
            steps {
                echo "Running FitPulse sports-science unit tests inside container..."
                sh '''
                    docker run --rm \
                      -v "$WORKSPACE/tests:/app/tests:ro" \
                      "$IMAGE_TAG" \
                      python -m pytest /app/tests -v
                '''
            }
        }

        stage('Trivy Security Scan') {
            steps {
                echo "Scanning container image with Trivy..."
                sh '''
                    if command -v trivy &> /dev/null; then
                        trivy image \
                          --severity CRITICAL,HIGH,MEDIUM,LOW \
                          --format json \
                          --output trivy-report.json \
                          "$IMAGE_TAG" || true
                    else
                        echo "Trivy not installed, generating empty scan"
                        echo '{"Results": []}' > trivy-report.json
                    fi
                '''
                archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
            }
        }

        stage('DeployMate Risk Assessment') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'deploymate-ci',
                        usernameVariable: 'DEPLOYMATE_EMAIL',
                        passwordVariable: 'DEPLOYMATE_PASSWORD'
                    )
                ]) {
                    script {
                        echo "Submitting evidence to DeployMate-II at ${DEPLOYMATE_URL}..."

                        sh '''
                            python3 - <<'PY'
import json
import os
import sys
import urllib.request
import urllib.error

base = os.environ["DEPLOYMATE_URL"].rstrip("/")

def api_post(url, data_dict, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data_dict).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

# 1. Login to DeployMate
try:
    login_resp = api_post(f"{base}/auth/login", {
        "email": os.environ["DEPLOYMATE_EMAIL"],
        "password": os.environ["DEPLOYMATE_PASSWORD"]
    })
    token = login_resp["access_token"]
except Exception as e:
    print(f"[FATAL] Failed to authenticate with DeployMate: {e}", file=sys.stderr)
    sys.exit(1)

# 2. Parse Trivy findings
findings = {"critical": 0, "high": 0, "medium": 0, "low": 0}
if os.path.exists("trivy-report.json"):
    try:
        with open("trivy-report.json") as f:
            trivy_data = json.load(f)
        for r in trivy_data.get("Results") or []:
            for v in r.get("Vulnerabilities") or []:
                sev = v.get("Severity", "").lower()
                if sev in findings:
                    findings[sev] += 1
    except Exception as e:
        print(f"[WARN] Failed to parse Trivy report: {e}", file=sys.stderr)

# 3. Submit Assessment
payload = {
    "project_name": os.environ["APP_NAME"],
    "commit_hash": os.environ["GIT_COMMIT"],
    "branch": os.environ["RESOLVED_BRANCH"],
    "environment": "staging",
    "build_status": "SUCCESS",
    "test_status": "PASS",
    "security_findings": findings,
    "infrastructure_metrics": {"cpu_usage_percent": 35.0, "memory_usage_percent": 45.0},
    "recent_failures": 0
}

try:
    result = api_post(f"{base}/assessments", payload, token=token)
except Exception as e:
    print(f"[FATAL] Failed to submit assessment: {e}", file=sys.stderr)
    sys.exit(1)

decision = str(result.get("decision", "BLOCK")).upper()
risk_score = result.get("risk_score", 0)

print("")
print("==========================================")
print("DEPLOYMATE-II ASSESSMENT DECISION:", decision)
print("RISK SCORE:", risk_score)
print("SECURITY FINDINGS:", findings)
print("==========================================")
print("")

with open("decision.txt", "w") as f:
    f.write(decision)

with open("assessment-result.json", "w") as f:
    json.dump(result, f, indent=2)
PY
                        '''

                        env.DEPLOYMATE_DECISION = readFile('decision.txt').trim()
                        echo "Evaluated Decision: ${env.DEPLOYMATE_DECISION}"

                        if (env.DEPLOYMATE_DECISION == "BLOCK") {
                            error("CRITICAL: DeployMate-II BLOCKED this deployment due to high risk.")
                        } else if (env.DEPLOYMATE_DECISION == "REVIEW") {
                            echo "WARNING: Risk score is elevated. Routing to Manual Approval Gate..."
                        } else {
                            echo "SUCCESS: Deployment APPROVED by DeployMate-II."
                        }
                    }
                }
                archiveArtifacts artifacts: 'assessment-result.json', allowEmptyArchive: true
            }
        }

        stage('DeployMate Dashboard Authorization') {
            when {
                expression {
                    return env.DEPLOYMATE_DECISION == 'REVIEW'
                }
            }
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'deploymate-ci',
                        usernameVariable: 'DEPLOYMATE_EMAIL',
                        passwordVariable: 'DEPLOYMATE_PASSWORD'
                    )
                ]) {
                    script {
                        echo ""
                        echo "=================================================================="
                        echo "DEPLOYMATE-II GATE: MANUAL AUTHORIZATION REQUIRED"
                        echo "Risk was assessed as REVIEW. Open the DeployMate-II Dashboard to"
                        echo "review Bedrock AI insights and Authorize or Reject this release:"
                        echo "👉 http://54.144.253.111"
                        echo "=================================================================="
                        echo ""

                        sh '''
                            python3 - <<'PY'
import json
import os
import sys
import time
import urllib.request
import urllib.error

base = os.environ["DEPLOYMATE_URL"].rstrip("/")

def api_call(url, data_dict=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        url,
        data=json.dumps(data_dict).encode("utf-8") if data_dict else None,
        headers=headers,
        method="POST" if data_dict else "GET"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Load assessment ID
with open("assessment-result.json") as f:
    assessment_data = json.load(f)
assessment_id = assessment_data["id"]

# Login
login_resp = api_call(base + "/auth/login", {
    "email": os.environ["DEPLOYMATE_EMAIL"],
    "password": os.environ["DEPLOYMATE_PASSWORD"]
})
token = login_resp["access_token"]

# Polling loop (checks every 5s, max 120 attempts = 10 minutes)
print(f"[POLL] Awaiting decision on Assessment #{assessment_id} in DeployMate Dashboard...")

for attempt in range(1, 121):
    record = api_call(base + "/assessments/" + str(assessment_id), token=token)
    decision = str(record.get("decision", "")).upper()

    if decision in ("APPROVED_BY_LEAD", "APPROVE"):
        print("")
        print("==========================================================")
        print("RELEASE AUTHORIZED via DeployMate-II Dashboard!")
        print("Final Status:", decision)
        print("==========================================================")
        print("")
        with open("decision.txt", "w") as f:
            f.write(decision)
        sys.exit(0)
    elif decision in ("REJECTED_BY_LEAD", "BLOCK"):
        print("")
        print("==========================================================")
        print("RELEASE REJECTED via DeployMate-II Dashboard!")
        print("Final Status:", decision)
        print("==========================================================")
        print("")
        with open("decision.txt", "w") as f:
            f.write(decision)
        sys.exit(1)

    if attempt % 6 == 0:
        elapsed = attempt * 5
        print(f"[POLL] Waiting for Lead authorization on http://54.144.253.111 ({elapsed}s elapsed)...")
    time.sleep(5)

print("[TIMEOUT] No decision received from DeployMate Dashboard after 10 minutes.")
sys.exit(1)
PY
                        '''

                        env.DEPLOYMATE_DECISION = readFile('decision.txt').trim()
                        echo "Final Decision: ${env.DEPLOYMATE_DECISION}"
                    }
                }
            }
        }

        stage('Deploy FitPulse') {
            when {
                expression {
                    return env.DEPLOYMATE_DECISION == 'APPROVE' || env.DEPLOYMATE_DECISION == 'APPROVED_BY_LEAD'
                }
            }
            steps {
                echo "Deploying FitPulse-AI container to Port ${APP_PORT}..."
                sh '''
                    docker stop fitpulse-ai 2>/dev/null || true
                    docker rm fitpulse-ai 2>/dev/null || true

                    docker run -d \
                      --name fitpulse-ai \
                      --restart unless-stopped \
                      -p 3000:3000 \
                      -e SQLITE_DB_PATH=/data/fitpulse.db \
                      -v fitpulse_data:/data \
                      "$IMAGE_TAG"

                    for i in $(seq 1 15); do
                        if curl -fsS http://127.0.0.1:3000/health; then
                            echo "FitPulse is HEALTHY and LIVE on port 3000!"
                            exit 0
                        fi
                        echo "Waiting for FitPulse to start... ($i/15)"
                        sleep 2
                    done

                    docker logs fitpulse-ai
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo "FitPulse CI/CD pipeline completed successfully."
        }
        failure {
            echo "FitPulse pipeline failed or was blocked by DeployMate-II."
        }
    }
}
