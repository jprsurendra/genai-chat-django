# Branch 008: `genai-chat-008-agent-tools` 🚀

**Goal:** 
Transform the chatbot into an autonomous AI Agent by implementing Function Calling (Tool Calling). The AI will be able to decide on its own when to use external tools (like a Calculator or Web Search) instead of hallucinating answers.

---

## 🛠️ Tools Implemented in this Branch

### 1. Calculator Tool
- **Problem:** LLMs are bad at math (as seen with `2+2`). They predict text, they don't calculate.
- **Solution:** A Python function `calculate(expression)` that uses safe `eval()` to compute exact math. The AI will call this tool when asked a math question.

### 2. Web Search Tool (Optional/Future)
- **Problem:** The AI's knowledge is limited to its training data (cutoff date).
- **Solution:** A tool that queries a search engine (like Tavily or DuckDuckGo) and returns real-time results.

### 3. Bigger Model Requirement
- **Problem:** Small models (1.5B/1B) cannot reliably output structured JSON for tool calling.
- **Solution:** Switch `OLLAMA_MODEL` to a larger model (e.g., `llama3.1:8b` or `qwen2.5:7b`) or use OpenAI (GPT-4o-mini).

---

## 🏗️ Architecture

1. User sends a message.
2. LLM checks if a tool is needed.
3. If yes, LLM outputs a `tool_call` (JSON).
4. Django executes the Python function.
5. Result is sent back to the LLM.
6. LLM generates the final answer using the tool's result.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस ब्रांच का मकसद:**
चैटबॉट को एक AI Agent में बदलना, जो अपनी बुद्धि से तय करे कि कब बाहरी टूल्स (जैसे Calculator) का इस्तेमाल करना है।

**टूल्स:**
1. **Calculator:** मैथ (गणित) के सवालों को सटीकता से हल करने के लिए।
2. **Web Search:** इंटरनेट से ताज़ा जानकारी लाने के लिए।
3. **Bigger Model:** छोटे मॉडल टूल कॉलिंग में कमज़ोर होते हैं, इसलिए हम `llama3.1:8b` या `gpt-4o-mini` का उपयोग करेंगे।

</details>