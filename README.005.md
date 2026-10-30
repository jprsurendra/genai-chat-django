# Branch 005: `genai-chat-005-db-auth` ✅ 

**Goal:** 
To transform the application from a prototype into a secure, multi-user platform. This branch introduces **MySQL** for persistent data storage, **JWT Authentication** for secure login/registration, and separates the **UI** from the **API** into distinct Django apps. It also adds chat history management (rename and delete) and permanent file storage for RAG.

---

## ⚙️ Database Migration (MySQL Setup)

To run this branch you must move from the default SQLite to MySQL. The steps below were written for Ubuntu/Debian.

### 1. Install MySQL Server

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

### 2. Create the database and user

Log into MySQL as root:

```bash
sudo mysql
```

Then run the following SQL (replace `your_password_here` with a strong password):

```sql
CREATE DATABASE genai_chat_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'genai_user'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON genai_chat_db.* TO 'genai_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> 💡 `utf8mb4` is important here: this app stores Hindi text and emojis in chat messages, and a plain `utf8` (3-byte) database can reject emojis.

### 3. Install the MySQL client for Python

Activate your virtual environment and install the driver:

```bash
pip install mysqlclient
```

If the install fails, install the system dependencies first and try again:

```bash
sudo apt install default-libmysqlclient-dev build-essential pkg-config
```

Add `mysqlclient` to `requirements.txt` as well, so other machines get it too.

### 4. Configure `.env`

Add your database credentials to the `.env` file in the project root:

```env
DB_NAME=genai_chat_db
DB_USER=genai_user
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=3306
```

> ⚠️ `.env` holds a real password. Keep it out of Git (it is already in `.gitignore`).

### 5. Update `local_settings.py`

Make sure `local_settings.py` reads these variables. It needs `import os`, and the `.env` file must be loaded (for example with `load_dotenv()`) before this block runs:

```python
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'genai_chat_db'),
        'USER': os.getenv('DB_USER', 'genai_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}
```

### 6. Run migrations

Apply the migrations to create the tables in MySQL:

```bash
python manage.py makemigrations
python manage.py migrate
```

To confirm the connection works, you can open a database shell:

```bash
python manage.py dbshell
```

### 🚨 Troubleshooting common migration errors

While setting up the database you may run into the errors below. Both fixes **delete data**, so use them in development only.

**Error 1: `It is impossible to add a non-nullable field 'file' to uploadeddocument without specifying a default.`**

*Cause:* you added a new field (`file`) to a model, but the table already has rows, and Django does not know what value to put in the new column for them.

*Fix:* if you do not care about the existing data (true during development), reset the `chat` app's migrations:

1. Delete all files inside `chat/migrations/` except `__init__.py`.
2. Drop the old tables and the old `chat` migration records in MySQL:

   ```sql
   USE genai_chat_db;
   DROP TABLE chat_uploadeddocument;
   DROP TABLE chat_chatmessage;
   DROP TABLE chat_chatsession;
   DELETE FROM django_migrations WHERE app = 'chat';
   EXIT;
   ```

3. Recreate and apply the migrations:

   ```bash
   python manage.py makemigrations chat
   python manage.py migrate
   ```

> ⚠️ Delete only the `chat` rows from `django_migrations`. If you drop the whole `django_migrations` table, Django forgets that the other tables (`auth_user`, `django_content_type`, ...) already exist, and you will get Error 2.

**Error 2: `MySQLdb.OperationalError: (1050, "Table 'django_content_type' already exists")`**

*Cause:* the `django_migrations` table was deleted, so Django thinks this is a fresh start, but the real tables (`django_content_type`, `auth_user`, ...) are still in the database from a previous run.

*Fix:* drop the whole database and recreate it clean:

```sql
DROP DATABASE genai_chat_db;
CREATE DATABASE genai_chat_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON genai_chat_db.* TO 'genai_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Then run the migrations again:

```bash
python manage.py migrate
```

---

## 🛠️ What Changed in this Branch?

### 1. Architecture: Separation of Concerns
- **New `accounts` App:** Exclusively handles user authentication (JWT Login/Register).
- **New `web_ui` App:** Exclusively handles rendering HTML templates and static files (CSS/JS). The `chat` app now strictly serves JSON APIs.
- **Database Migration:** Migrated from SQLite to **MySQL**.

### 2. Security: JWT Authentication
- **User Registration:** Users can register with a username, email, and password (with confirmation).
- **JWT Tokens:** Upon successful login, the backend issues an `access` and `refresh` token. The frontend stores the `access` token in `localStorage` and attaches it to every API request via the `Authorization: Bearer <token>` header.
- **Protected Endpoints:** All chat, upload, and history endpoints now require a valid JWT. Unauthenticated requests receive a `401 Unauthorized` response.
- **Auto-Logout:** If a token is expired or invalid (401), the frontend automatically redirects the user to the login page.

### 3. Persistent Chat History & Management
- **Django Models:** Created `ChatSession`, `ChatMessage`, and `UploadedDocument` models.
- **Auto-Save:** When a user sends a message and the AI replies, both messages are saved to MySQL under the user's `ChatSession`.
- **History API:** A new `/api/chat/history` endpoint fetches past conversations for the logged-in user.
- **Rename & Delete:** Users can rename a chat (`PATCH` request) or soft-delete it (`DELETE` request). Soft delete means the data stays in the database but is hidden from the UI.

### 4. Permanent File Storage (User-Based)
- **User Folders:** Uploaded files are saved permanently in `media/documents/user_<id>/`.
- **Database Link:** The file path and URL are stored in the `UploadedDocument` model.
- **UI Display:** Files appear as chat bubbles (with timestamps) in the history, and users can click them to download.

> 💡 Add `media/` to `.gitignore`. Uploaded user files should not end up in the repository.

### 5. UI/UX Improvements
- **Login/Register Page:** A clean Bootstrap interface with tabs for Login and Register. Includes client-side validation for password matching.
- **Session Management:** The frontend checks for a token on page load. If missing or expired, it redirects to the login page.
- **Logout Button:** Clears tokens from `localStorage` and redirects to the login screen.

---

## 🐛 Major Bugs Fixed
1. **`SynchronousOnlyOperation` in Streaming:** Fixed by wrapping the database save operation inside `sync_to_async()` when the AI finishes streaming.
2. **Upload File Name:** Fixed the issue where temporary file names (e.g., `tmp123.pdf`) were saved instead of the original filename. `original_filename` is now passed through the view to the RAG engine.
3. **Missing Migrations:** Added `django.contrib.admin`, `auth`, and `sessions` to `INSTALLED_APPS` and updated `MIDDLEWARE` to prevent `SystemCheckError`.
4. **Template Paths:** Correctly mapped the new `web_ui` templates (`chat.html` and `login.html`).
5. **Media URL Link:** Fixed the download link for attachments. The frontend now makes sure the link starts with `/media/`, so Django serves the file instead of returning a `404 Page not found`.
6. **Attachment Ordering:** Fixed attachments appearing at the bottom of the chat. The frontend now combines messages and attachments into one array, sorts them by timestamp, and renders them in chronological order.

---

## 🎓 Educational Takeaways

1. **Why use MySQL over SQLite?** SQLite is great for local testing, but MySQL handles concurrent users, complex queries, and data integrity much better for production.
2. **JWT vs. Session ID:** The previous `X-Session-Id` was just a random string in the browser (data scoping). JWT is **identity verification**—it is cryptographically signed by the server, so it cannot be spoofed.
3. **Separation of Apps:** By splitting `web_ui`, `accounts`, and `chat`, the codebase is much easier to maintain. If you wanted to switch to React later, you would only delete `web_ui` and keep the APIs intact.
4. **Async + DB:** Django ORM is synchronous. When you are in an `async def` function (like SSE streaming), you must use `sync_to_async` to interact with the database, or the ASGI server will crash.
5. **File storage best practices:** Never save uploads in the project root or in one flat folder. A layout like `media/documents/user_<id>/` keeps things organised and makes it easy to delete all files of a user if they delete their account.

---

## 🚀 Next Steps for Branch 006
- [ ] **Advanced RAG:** Implement Hybrid Search (BM25 + Vector) and Query Rewriting.
- [ ] **User Feedback:** Add 👍/👎 buttons on chat responses to collect data for evaluation.
- [ ] **UI Polish:** Add a dark mode toggle and a loading spinner for file uploads.
- [ ] **Stop Generation Button:** Implement `AbortController` in JS to stop the AI mid-response.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस ब्रांच का मकसद:**
ऐप को एक सुरक्षित और मल्टी-यूज़र प्लेटफॉर्म बनाना। इसमें हमने **MySQL डेटाबेस**, **JWT लॉगिन/रजिस्टर**, और **UI को API से अलग** करने का काम किया।

**मुख्य बदलाव:**
1. **आर्किटेक्चर:** हमने `accounts` (लॉगिन के लिए) और `web_ui` (HTML/JS के लिए) नाम के दो नए ऐप बनाए। अब `chat` ऐप सिर्फ JSON API का काम करता है।
2. **सुरक्षा:** `X-Session-Id` की जगह JWT टोकन का उपयोग किया। अब हर रिक्वेस्ट के साथ `Authorization: Bearer <token>` हेडर जाता है। बिना लॉगिन के कोई भी चैट नहीं कर सकता।
3. **चैट हिस्ट्री:** अब यूज़र के सारे मैसेज और AI के जवाब MySQL डेटाबेस में सेव होते हैं। पेज रिफ्रेश करने पर भी चैट नहीं जाएगी।
4. **बग्स:** स्ट्रीमिंग के दौरान आने वाला `SynchronousOnlyOperation` एरर ठीक किया, और फाइल अपलोड करते समय टेम्परेरी नाम के बजाय असली फाइल का नाम सेव करने का लॉजिक जोड़ा।
5. **MySQL setup:** Ubuntu पर `mysql-server` install करें, `utf8mb4` वाला database और user बनाएँ, `mysqlclient` install करें, `.env` में DB की details डालें और `python manage.py migrate` चलाएँ। (`utf8mb4` इसलिए ज़रूरी है ताकि Hindi text और emojis सही से save हों।)
6. **फाइल स्टोरेज:** अपलोड की गई फाइलें `media/documents/user_<id>/` फोल्डर में हमेशा के लिए सेव होती हैं, और chat में उनका download link भी दिखता है।
7. **नई सुविधाएँ:** अब आप chat का नाम बदल सकते हैं (Rename) और उसे delete कर सकते हैं। Delete "soft delete" है, यानी data database में रहता है पर UI में नहीं दिखता।

**माइग्रेशन में आने वाली समस्या:**
अगर `Table already exists` या `non-nullable field` जैसी error आए, तो इसका मतलब है कि database में पुराना data है। Development में सबसे आसान तरीका: `chat/migrations/` की सारी files delete करें (सिर्फ़ `__init__.py` छोड़कर), MySQL में `chat` की पुरानी tables drop करें और `django_migrations` में से सिर्फ़ `chat` वाली rows delete करें, फिर `makemigrations` और `migrate` चलाएँ। पूरी `django_migrations` table drop न करें, वरना `Table already exists` error आ जाएगी। यह सब data मिटा देता है, इसलिए सिर्फ़ development में करें।

</details>