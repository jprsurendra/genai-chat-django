**Issue found during testing**

With the small local models (`qwen2.5:1.5b`, `llama3.2:1b`), an ambiguous prompt confused the model:

| # | User message | Model behaviour |
|---|--------------|-----------------|
| 1 | `I am SSR, 2+2?` | Ignored the math and invented a story about "SSR" being a Russian military unit |
| 2 | `I am SSR. 2+2?` | Repeated the same wrong "SSR" explanation |
| 3 | `My name is SSR. and i want do calculate by you 2+2` | Correct: `The answer to 2+2 is 4.` |


[![Issue found during Testing Branch 001](docs/screenshot_002.png)](docs/screenshot_002.png)

*Screenshot (Issue found during Testing Branch 001): small model confused by `I am SSR, 2+2?` — [`docs/screenshot_002.png`](docs/screenshot_002.png)*
**Deep Dive into Model Behavior (Screenshot Analysis)**

This screenshot is a perfect example of the difference between small local AI models (like `qwen2.5:1.5b` or `llama3.2:1b`) and large models (like ChatGPT-4). Here is an analysis of what happened:

**Takeaways**

- Small models (1B–1.5B parameters) are easily distracted by names and abbreviations in short, ambiguous prompts.
- They predict the next token; they do not reliably calculate. Clear, complete prompts give far better results.
- The current system prompt gives the model no guidance on how to prioritise the user's actual question. This is addressed in the next branch.


🕵️ **What went wrong in the chat?**
- **The "SSR" Confusion:** When the prompt was `"I am SSR, 2+2?"`, the AI completely misunderstood the intent. It ignored the math and thought the user was talking about a Russian military unit (Special Security Reserve).
- **Prompt Misinterpretation:** The AI got stuck trying to define what "SSR" means, completely forgetting the 2+2 calculation.
- **The Final Success:** When the prompt was changed to `"My name is SSR. and i want do calculate by you 2+2"`, the structure was much clearer to the AI. It finally understood the math and gave the correct answer: **4**.

🧠 **Why did this happen? (The LLM Truth)**
- **Small Models are Literal:** 1B or 1.5B parameter models are very small. If you give them a short or slightly ambiguous sentence (`"I am SSR, 2+2?"`), they easily get confused.
- **Context is Everything:** In the final prompt, the user provided clear context (`"My name is SSR"` + `"i want do calculate"`). The AI used this context to finally give the right answer.
- **No Math Engine:** LLMs don't actually "calculate" like a calculator; they predict the next word. Small models are notoriously bad at math unless the prompt is extremely clear.

🛠️ **How to fix this?**
Since this is an educational app, here are 3 ways to make the AI smarter without changing the model:
1. **Update the `SYSTEM_PROMPT`:** Make it stricter so the AI focuses on the user's actual intent. (*This is being addressed in Branch 002*).
   <br>In your `"config/settings.py"`, your current system prompt is a bit too simple. Let's make it stricter so the AI focuses on the user's actual intent.
   <br>
   ```
      SYSTEM_PROMPT = (
          "You are a helpful, smart AI assistant. "
          "Always focus on answering the user's primary question (like math or coding) "
          "rather than getting confused by names or titles in the prompt. "
          "Use markdown for formatting."
      )
   ```
2. **Try the bigger model:** Switch from `qwen2.5:1.5b` to `llama3.2:1b`. *(If you have 8GB+ RAM, try `llama3.1:8b` for mind-blowing results!)*
3. **How to prompt small models:** Be direct. 
   - ❌ **Bad:** `I am SSR, 2+2?`
   - ✅ **Good:** `Calculate 2+2.`


<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

यह स्क्रीनशॉट एक बहुत ही बढ़िया उदाहरण है कि **छोटे लोकल AI मॉडल्स** (जैसे हमारे `qwen2.5:1.5b` या `llama3.2:1b`) और **बड़े मॉडल्स** (जैसे ChatGPT-4) के दिमाग में क्या फर्क होता है।

**🕵️ चैट में क्या गड़बड़ हुई?**
1. **"SSR" का कन्फ्यूजन:** आपने लिखा *"I am SSR, 2+2?"*। AI ने आपके सवाल को गलत समझ लिया। इसने मैथ (गणित) को इग्नोर कर दिया और सोचने लगा कि आप रूसी सेना की किसी यूनिट (Special Security Reserve) की बात कर रहे हैं।
2. **Prompt को गलत समझना:** AI "SSR" का मतलब ढूँढने में उलझ गया और 2+2 को भूल गया।
3. **आखिर में सही जवाब:** जब आपने लिखा *"My name is SSR. and i want do calculate by you 2+2"*, तो आपका वाक्य बहुत साफ था। AI तुरंत समझ गया और सही जवाब दिया: **4**।

**🧠 ऐसा क्यों हुआ? (AI की सच्चाई)**
* **छोटे मॉडल्स बहुत सीधे होते हैं:** 1B या 1.5B पैरामीटर वाले मॉडल्स बहुत छोटे होते हैं। अगर आप कोई छोटा या अधूरा वाक्य लिखेंगे (जैसे *"I am SSR, 2+2?"*), तो वे आसानी से कन्फ्यूज हो जाते हैं।
* **Context (संदर्भ) सब कुछ है:** आपके आखिरी सवाल में पूरा संदर्भ था (*"मेरा नाम SSR है"* और *"मुझे 2+2 करना है"*)। AI ने इसी संदर्भ को समझकर सही जवाब दिया।
* **AI कैलकुलेटर नहीं है:** AI असल में गणित नहीं करता, वह बस अगला शब्द अनुमान लगाता है (Predict करता है)। छोटे मॉडल्स गणित में बहुत कमजोर होते हैं, जब तक कि सवाल बहुत साफ-साफ न लिखा हो।

**🛠️ अपने ऐप में इसे कैसे सुधारें?**
1. **`SYSTEM_PROMPT` को अपडेट करें:** (जो हम ब्रांच 002 में कर रहे हैं)।
2. **बड़े मॉडल का इस्तेमाल करें:** `llama3.2:1b` (main) पर स्विच करें।
3. **छोटे मॉडल्स से सवाल कैसे पूछें?** सीधे और साफ शब्दों में पूछें (जैसे: `Calculate 2+2.`)।

</details>