# Branch 008: `genai-chat-008-agent-tools` 🚀

**Goal:** 
Transform the chatbot into an autonomous AI Agent by implementing Function Calling (Tool Calling). The AI will be able to decide on its own when to use external tools (like a Calculator or Web Search) instead of hallucinating answers.

---

## 🧠 LLM Selection Strategy: the full discussion

Before writing any tool code we had to answer one question: **which model will actually call the tools?** This section records how we got to the answer, including the options we rejected, so the decision is easy to revisit later.

### 1. The starting problem

- Tool calling means the model must output a **structured JSON request** (for example `{"tool": "calculate", "expression": "1234 * 5678"}`) at the right moment, and stay silent about tools when they are not needed.
- Our current local models (`qwen2.5:1.5b` and `llama3.2:1b`) are too small for this. We already saw them fail at much simpler things in Branch 002 (the "I am SSR, 2+2?" confusion).
- The development machine is a **16 GB RAM laptop** that also runs the IDE, a browser, MySQL, Redis and the Django server. That limits what can run locally.

### 2. Models we looked at

We started from a list of the big open-source and open-weight model families: DeepSeek, Llama, Qwen and Google Gemma. The question was which of them can run on this laptop *and* handle tool calling.

| Model | What it is good at | Can it run on this laptop? | Verdict |
|-------|--------------------|----------------------------|---------|
| Llama 3.1 8B | Most widely used open model for function calling; reliable JSON output | On paper yes (about 4.7 GB), but too heavy next to the IDE, MySQL and browser | Best local choice if the hardware allowed it |
| Qwen 2.5 7B | Good at tool calling and multilingual text, including Hindi | Same problem as the 8B model | Second choice |
| Qwen 2.5 3B | Much smarter than 1.5B, produces JSON reasonably well | Yes (about 1.9 GB) | Candidate for "Plan B" (below) |
| Llama 3.2 3B | Small but capable, supports tool calling | Yes (about 2 GB) | Candidate for "Plan B" |
| Phi-3 Mini | Good reasoning and maths for its size | Yes (about 2.3 GB) | Considered, but we did not verify its tool calling |
| DeepSeek R1 / V3 | Deep reasoning, maths, coding | No, far too large locally | Only useful through an API |
| Llama 3.3 70B | Strong tool calling | No (needs tens of GB) | Only through an API |
| Gemma | Lightweight, multimodal | Small versions can run locally | Mainly reachable through Google AI Studio |

The honest summary: the models that are good at tool calling are either too big for this laptop, or (at 3B) borderline.

### 3. Plan B: stay fully local with a 3B model

If cloud is not an option, the fallback is a 3B model:

```bash
ollama pull qwen2.5:3b
```

```env
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_MODEL_FAST=qwen2.5:1.5b
```

To make this safer, add a **Python-level fallback** so we do not depend on the model alone: if the question contains maths symbols such as `+`, `-`, `*` or `/` together with numbers, call the calculator directly. The catch is false positives (for example "2-3 days"), so the check should look for a real arithmetic expression, not just a symbol.

### 4. Website vs API

A point that is easy to miss: the free chat **websites** (DeepSeek Chat, Meta AI, Hugging Face Chat, Google AI Studio's chat) are user interfaces for people. Our Django app cannot talk to them. It needs an **API**, a programmatic endpoint that takes a message and returns JSON.

So "this model is free on a website" does not mean "we can use it in the app". We need a provider that offers a free API.

### 5. Free cloud API options evaluated

1. **OpenRouter (selected ✅):** one API key gives access to many models (DeepSeek R1, Llama 3.3 70B, Qwen 2.5 72B and more). It is OpenAI-compatible, so our existing `openai` SDK code keeps working; only the base URL and model name change. Free variants have a `:free` suffix on the model name.
2. **Groq:** the fastest option (Llama 3.3 70B), great for instant streaming, and it supports tool calling. We chose OpenRouter for model variety, but Groq stays a good second option.
3. **DeepSeek API:** the official API is cheap and OpenAI-compatible, but it only gives us DeepSeek models.
4. **Google AI Studio:** the official route to Gemma and Gemini, but it uses a different client library, so it is not a drop-in change for our code. We judged Llama 3.3 the safer choice for tool calling.

### 6. Decision: a hybrid approach

- **Local (Ollama):** keep `qwen2.5:1.5b` for fast, simple chat, with no internet required.
- **Cloud (OpenRouter):** use `meta-llama/llama-3.3-70b-instruct:free` for **Agent Tools**, where reasoning quality matters most.

In practice this is a provider switcher: local when you want privacy and offline use, cloud when you need a smarter model.

> ℹ️ Free model names and limits change over time. Check OpenRouter's model list before relying on a specific `:free` model.

### 7. Trade-offs we accept with the cloud option

- **Privacy:** the main README promises that no data leaves the machine. With a cloud provider, the user's message and any retrieved document text are sent to a third party. This matters especially after the security work in Branch 007, and it should be stated clearly in the docs and, ideally, in the UI.
- **Rate limits and availability:** free tiers have request limits, and a free model can be slow or temporarily unavailable.
- **Internet dependency:** cloud mode does not work offline. Local mode still does.

### 8. How to connect OpenRouter

**1. Get an API key.** Sign up on OpenRouter, open the **Keys** section and create a key (it starts with `sk-or-v1-`).

**2. Configure `.env`:**

```env
# ---- LLM Provider ----
# 'ollama' (local) or 'openai' (cloud)
LLM_PROVIDER=openai

# ---- OpenRouter settings ----
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

> ⚠️ The API key is a secret. It lives in `.env`, which must stay out of Git.

**3. Read the base URL in `local_settings.py`:**

```python
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
```

**4. Use it in `chat/utilities/llms/llm.py`** by updating `_create_client`:

```python
def _create_client(self) -> tuple[AsyncOpenAI, str]:
    if settings.LLM_PROVIDER == "ollama":
        return (
            AsyncOpenAI(base_url=settings.OLLAMA_BASE_URL, api_key="ollama"),
            settings.OLLAMA_MODEL,
        )

    # OpenAI / OpenRouter
    return (
        AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1"),
        ),
        settings.OPENAI_MODEL,
    )
```

**5. Restart the server and test** with a normal question. The answer should now come from the 70B model, without using any laptop RAM.

---

## 🛠️ Tools in this Branch

### 1. Calculator Tool
- **Problem:** LLMs are bad at math (as seen with `2+2`). They predict text, they don't calculate.
- **Solution:** A Python function `calculate(expression)` that uses safe `eval()` to compute exact math. The AI will call this tool when asked a math question.

### 2. Web Search Tool (Optional/Future)
- **Problem:** The AI's knowledge is limited to its training data (cutoff date).
- **Solution:** A tool that queries a search engine (like Tavily or DuckDuckGo) and returns real-time results. It needs a free search API, so it comes after the calculator.

### 3. Database Query Tool (Planned, last)
- **Use case:** questions such as "how many chats do I have?" or "how many files did I upload?".
- **Approach:** a read-only query, scoped to the logged-in user. This is the riskiest tool for data leaks, which is why Branch 007 (security hardening) comes first.

### Order of work
1. Build the calculator in `tools.py`.
2. Add the function-calling logic in `LLMService`.
3. Connect OpenRouter (or Groq) so a capable model is available.
4. Add web search and the database query tool last.

---

## 🏗️ Architecture (How Tool Calling Works)

1. User sends a message (e.g., "What is 1234 * 5678?").
2. Django sends the message + a list of **available tools** to the LLM.
3. The LLM does not answer directly. Instead, it outputs a `tool_call` JSON: `{"tool": "calculate", "expression": "1234 * 5678"}`.
4. Django executes the Python `calculate()` function and gets `7006652`.
5. Django sends this result back to the LLM.
6. The LLM generates the final natural language answer: *"The answer is 7,006,652."*

---

## 🎓 Educational Takeaways

1. **Hardware is a real constraint:** Not everyone has an RTX 4090. Cloud APIs bridge the gap between local hardware limitations and the need for powerful reasoning.
2. **A free website is not a free API:** A chat UI is for people. A Django app needs an API endpoint.
3. **OpenAI SDK is the industry standard:** Because Ollama, OpenRouter, and Groq all support the OpenAI format, we can switch providers by changing just a few lines in `.env`.
4. **Cloud has a price even when it is free:** privacy, rate limits and internet dependence. Know what you give up.
5. **Do not trust the model alone:** a simple Python fallback for the calculator makes the app work even when a small model fails to call the tool.
6. **Tool Calling is the future:** A chatbot that just talks is limited. An agent that can calculate, search, and query databases is exponentially more useful.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस ब्रांच का मकसद:**
चैटबॉट को एक AI Agent में बदलना, जो अपनी बुद्धि से तय करे कि कब बाहरी tools (जैसे Calculator) का इस्तेमाल करना है।

**LLM चुनने की पूरी चर्चा:**

1. **समस्या:** Tool calling के लिए model को सही समय पर सही JSON देना पड़ता है। हमारे छोटे models (1.5B, 1B) इसमें कमज़ोर हैं। और लैपटॉप में सिर्फ़ 16GB RAM है, जिसमें IDE, browser, MySQL और Django server भी चलते हैं।
2. **Local models जो देखे:** Llama 3.1 8B और Qwen 2.5 7B tool calling में अच्छे हैं, पर इस लैपटॉप पर भारी पड़ते हैं। Qwen 2.5 3B और Llama 3.2 3B (लगभग 2GB) हल्के हैं और "Plan B" बन सकते हैं। DeepSeek R1 और Llama 3.3 70B इतने बड़े हैं कि local नहीं चल सकते।
3. **Website बनाम API:** DeepSeek Chat, Meta AI जैसी websites इंसानों के लिए हैं। हमारा Django app उनसे बात नहीं कर सकता, उसे API चाहिए।
4. **Free Cloud API:** OpenRouter (चुना गया ✅), Groq (सबसे तेज़), DeepSeek API और Google AI Studio। OpenRouter OpenAI-compatible है, इसलिए हमारा `openai` SDK वाला code लगभग वैसा ही चलता है।
5. **फ़ैसला (Hybrid):** सादा chat के लिए local `qwen2.5:1.5b`, और Agent Tools के लिए OpenRouter का `llama-3.3-70b-instruct:free`।
6. **ध्यान रखें:** Cloud में आपका message और documents का text तीसरे पक्ष को जाता है (privacy), free tier की limits होती हैं, और internet चाहिए। Free model के नाम समय के साथ बदल सकते हैं, इसलिए OpenRouter की list देख लें।
7. **Plan B / Fallback:** अगर model tool call न कर पाए, तो Python में ऐसा check लगाएँ कि सवाल में असली गणित (संख्याएँ और `+ - * /`) हो तो सीधे Calculator चल जाए।

**मुख्य बदलाव:**
- **Calculator:** गणित के सवाल सटीकता से हल करने के लिए।
- **Tool Calling:** अब AI खुद समझेगा कि जवाब देने के लिए Calculator चलाना है, और JSON में request देगा।
- **काम का क्रम:** पहले Calculator, फिर function-calling logic, फिर OpenRouter, और सबसे आख़िर में Web Search और Database query।

</details>