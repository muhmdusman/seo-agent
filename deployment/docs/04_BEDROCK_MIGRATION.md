# 🚀 Migrating from Mistral AI to AWS Bedrock

## Why Switch to Bedrock?

1. **✅ No Timeout Issues** - Your current Mistral timeouts (>2 minutes) will be solved
2. **✅ Native AWS** - Runs in same region as your ECS (lower latency)
3. **✅ Multiple Models** - Claude, Nova, Llama, Mistral (all available)
4. **✅ Better Pricing** - Pay per token, no subscription needed
5. **✅ IAM Auth** - No API keys needed, uses AWS credentials

---

## Cost Comparison

### Current: Mistral AI
```
- API subscription or pay-per-use
- External API calls (slower)
- Timeout issues
```

### AWS Bedrock Nova Lite (Recommended for your use case)
```
Input:  $0.06 per 1M tokens
Output: $0.24 per 1M tokens

Example (100 analyses per month):
- Average prompt: 5,000 tokens
- Average response: 2,000 tokens
- Cost: (5k × 100 × $0.06/1M) + (2k × 100 × $0.24/1M) = $0.30 + $0.48 = $0.78/month
```

### AWS Bedrock Claude 3.5 Haiku (Better Quality)
```
Input:  $0.80 per 1M tokens
Output: $4.00 per 1M tokens

Same usage: ~$10-15/month
```

---

## 📝 Migration Steps

### Step 1: Update Code (5 minutes)

**File: `backend/agents/weekly_agent.py`**

**OLD:**
```python
from langchain_mistralai import ChatMistralAI

self.llm = ChatMistralAI(
    model_name="mistral-large-latest",
    api_key=settings.MISTRAL_API_KEY,
    temperature=0,
    timeout=120,
    max_retries=3,
)
```

**NEW (Bedrock Nova):**
```python
from langchain_aws import ChatBedrock

self.llm = ChatBedrock(
    model_id="us.amazon.nova-lite-v1:0",  # or "us.amazon.nova-pro-v1:0"
    region_name="us-east-1",  # Same region as your ECS
    model_kwargs={
        "temperature": 0,
        "max_tokens": 4096,
    }
)
```

**NEW (Bedrock Claude):**
```python
from langchain_aws import ChatBedrock

self.llm = ChatBedrock(
    model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
    region_name="us-east-1",
    model_kwargs={
        "temperature": 0,
        "max_tokens": 4096,
    }
)
```

**NEW (Bedrock Mistral):**
```python
from langchain_aws import ChatBedrock

self.llm = ChatBedrock(
    model_id="mistral.mistral-large-2407-v1:0",
    region_name="us-east-1",
    model_kwargs={
        "temperature": 0,
        "max_tokens": 4096,
    }
)
```

---

### Step 2: Update Environment Variables

**Remove:**
```bash
MISTRAL_API_KEY=xxx  # Not needed anymore!
```

**Add (optional):**
```bash
AWS_REGION=us-east-1  # Or use AWS_DEFAULT_REGION
BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
```

---

### Step 3: Update Config

**File: `backend/core/config.py`**

**Remove:**
```python
MISTRAL_API_KEY: str
```

**Add (optional):**
```python
BEDROCK_MODEL_ID: str = "us.amazon.nova-lite-v1:0"
AWS_REGION: str = "us-east-1"
```

---

### Step 4: Setup AWS Credentials in ECS

#### Option A: Use ECS Task IAM Role (Recommended)

**Create IAM Role Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/us.amazon.nova-lite-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
      ]
    }
  ]
}
```

**Attach to ECS Task Role:**
```bash
# Create policy
aws iam create-policy \
    --policy-name BedrockInvokePolicy \
    --policy-document file://bedrock-policy.json

# Attach to task role
aws iam attach-role-policy \
    --role-name ecsTaskRole \
    --policy-arn arn:aws:iam::ACCOUNT_ID:policy/BedrockInvokePolicy
```

**Update ECS Task Definition:**
```json
{
  "family": "seo-agent-backend",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskRole",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  ...
}
```

#### Option B: Use AWS Credentials (Not Recommended)

Add to ECS task definition environment:
```json
{
  "name": "AWS_ACCESS_KEY_ID",
  "value": "AKIA..."
},
{
  "name": "AWS_SECRET_ACCESS_KEY",
  "value": "..."
}
```

**⚠️ Use Option A (IAM Role) - more secure!**

---

### Step 5: Enable Bedrock Models

**AWS Console:**
1. Go to **AWS Bedrock Console**
2. Click **Model access** (left sidebar)
3. Click **Manage model access**
4. Enable:
   - ✅ Amazon Nova Lite
   - ✅ Amazon Nova Pro (optional)
   - ✅ Claude 3.5 Haiku (optional)
5. Click **Save changes**

**CLI:**
```bash
aws bedrock get-foundation-model \
    --model-identifier us.amazon.nova-lite-v1:0 \
    --region us-east-1
```

---

### Step 6: Test Locally

**Update `.env`:**
```bash
# Remove or comment out
# MISTRAL_API_KEY=xxx

# Add AWS credentials for local testing
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

**Test:**
```bash
cd backend
uvicorn main:app --reload
```

Visit: `http://localhost:8000` and test analysis!

---

### Step 7: Deploy to ECS

**GitHub Actions will automatically:**
1. Build new Docker image (with Bedrock code)
2. Push to ECR
3. Update ECS service
4. Use IAM role for Bedrock access

No manual deployment needed! Just push to GitHub.

---

## 🔍 Available Bedrock Models

### Amazon Nova (NEW - Best for your use case)

```python
# Nova Lite - Fastest, cheapest
model_id = "us.amazon.nova-lite-v1:0"
# Cost: $0.06 input / $0.24 output per 1M tokens
# Speed: ~1-2 seconds for your use case
# Quality: Good for SEO analysis

# Nova Pro - Better quality
model_id = "us.amazon.nova-pro-v1:0"
# Cost: $0.80 input / $3.20 output per 1M tokens
# Speed: ~2-4 seconds
# Quality: Excellent for detailed analysis
```

### Anthropic Claude

```python
# Claude 3.5 Haiku - Fast & High Quality
model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
# Cost: $0.80 input / $4.00 output per 1M tokens
# Speed: ~2-3 seconds
# Quality: Excellent reasoning

# Claude 3.5 Sonnet - Best Quality
model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
# Cost: $3.00 input / $15.00 output per 1M tokens
# Speed: ~3-5 seconds
# Quality: Best available
```

### Meta Llama

```python
# Llama 3.2 90B
model_id = "meta.llama3-2-90b-instruct-v1:0"
# Cost: $2.65 input / $3.50 output per 1M tokens
# Speed: ~2-4 seconds
# Quality: Very good
```

### Mistral (via Bedrock)

```python
# Mistral Large 2
model_id = "mistral.mistral-large-2407-v1:0"
# Cost: $2.40 input / $7.20 output per 1M tokens
# Speed: ~2-3 seconds (faster than Mistral AI API!)
# Quality: Same as current, but no timeout issues
```

---

## 🎯 Recommended Model

### For Personal Use (Your Case):

**Amazon Nova Lite** ✅
- Cheapest: ~$1-2/month
- Fast: 1-2 seconds
- Good quality for SEO analysis
- No timeout issues
- Native AWS (lowest latency)

```python
self.llm = ChatBedrock(
    model_id="us.amazon.nova-lite-v1:0",
    region_name="us-east-1",
    model_kwargs={
        "temperature": 0,
        "max_tokens": 4096,
    }
)
```

### If You Need Better Quality:

**Claude 3.5 Haiku** ✅
- Moderate cost: ~$10-15/month
- Fast: 2-3 seconds
- Excellent quality
- Great reasoning

```python
self.llm = ChatBedrock(
    model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
    region_name="us-east-1",
    model_kwargs={
        "temperature": 0,
        "max_tokens": 4096,
    }
)
```

---

## 📊 Full Comparison

| Feature | Mistral AI (Current) | Nova Lite | Claude Haiku | Nova Pro |
|---------|---------------------|-----------|--------------|----------|
| **Timeout Issues** | ❌ Yes (>2min) | ✅ No | ✅ No | ✅ No |
| **Speed** | Slow (>2min) | Fast (1-2s) | Fast (2-3s) | Medium (3-4s) |
| **Cost/100 analyses** | Unknown | $0.78 | $10-15 | $4-6 |
| **Quality** | Good | Good | Excellent | Excellent |
| **AWS Integration** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **API Key Needed** | ✅ Yes | ❌ No | ❌ No | ❌ No |

---

## 🔧 Complete Code Change

**File: `backend/agents/weekly_agent.py`**

```python
import logging

from datetime import date, timedelta
from urllib.parse import urljoin

# OLD: from langchain_mistralai import ChatMistralAI
from langchain_aws import ChatBedrock  # NEW

from core.config import settings

from tools.search_console_tool import (
    collect_search_console_data,
)
from tools.user_context_tool import (
    create_user_context_tool,
)
from tools.website_tool import (
    scrape_website,
)


logger = logging.getLogger(__name__)


class WeeklyAgent:

    def __init__(self, db):

        self.user_tool = create_user_context_tool(db)

        # OLD:
        # self.llm = ChatMistralAI(
        #     model_name="mistral-large-latest",
        #     api_key=settings.MISTRAL_API_KEY,
        #     temperature=0,
        #     timeout=120,
        #     max_retries=3,
        # )

        # NEW:
        self.llm = ChatBedrock(
            model_id="us.amazon.nova-lite-v1:0",  # or your preferred model
            region_name="us-east-1",  # same region as ECS
            model_kwargs={
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    # ... rest of the code stays the same ...
```

**That's it! Just 5 lines changed!**

---

## ✅ Migration Checklist

- [ ] Update `weekly_agent.py` (change import + llm initialization)
- [ ] Remove `MISTRAL_API_KEY` from environment variables
- [ ] Enable Bedrock models in AWS Console
- [ ] Create IAM policy for Bedrock access
- [ ] Attach policy to ECS task role
- [ ] Update ECS task definition with task role
- [ ] Test locally with AWS credentials
- [ ] Push to GitHub (auto-deploys via Actions)
- [ ] Test in production
- [ ] Monitor CloudWatch logs for any errors

---

## 🐛 Troubleshooting

### Error: "Could not resolve credentials"
**Solution:** Make sure ECS task has IAM role with Bedrock permissions

### Error: "Model not found"
**Solution:** Enable model in Bedrock console (Model access)

### Error: "Access denied"
**Solution:** Check IAM policy has `bedrock:InvokeModel` permission

### Error: "Region not available"
**Solution:** Bedrock available in: us-east-1, us-west-2, eu-west-1, ap-southeast-1

---

## 🎉 Benefits After Migration

1. ✅ **No More Timeouts** - Responses in 1-3 seconds vs 2+ minutes
2. ✅ **Lower Cost** - ~$1-15/month vs Mistral subscription
3. ✅ **Better Reliability** - AWS infrastructure
4. ✅ **Lower Latency** - Same AWS region
5. ✅ **No API Keys** - IAM role authentication
6. ✅ **Multiple Models** - Easy to switch anytime
7. ✅ **Better Monitoring** - CloudWatch built-in

---

**Ready to migrate? It's just 5 minutes of code changes!** 🚀
