from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 第一步：設定你的 Google Generative AI API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 選擇要使用的模型 (依你的權限及可用模型為準)
model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")

# --------------------------------------------------
# 1. 用 Flask 提供前端的 HTML 頁面
# --------------------------------------------------
@app.route('/', methods=['GET'])
def index():
    # 直接把原本的 index.html 內容放到字串中回傳
    return """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>語音辨識系統</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }
        select, button {
            font-size: 18px;
            margin: 10px;
            padding: 8px 16px;
        }
        .output-container {
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }
        .output-box {
            flex: 1;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
            min-height: 100px;
            text-align: left;
        }
        #status {
            margin: 10px 0;
            color: #666;
        }
        .output-label {
            font-weight: bold;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <h1>語音辨識系統</h1>
    <div>
        <select id="languageSelect">
            <option value="yue-Hant-HK">廣東話</option>
            <option value="zh-TW">中文</option>
            <option value="en-US">English</option>
        </select>
        <button id="startButton">開始錄音</button>
        <button id="stopButton" disabled>停止錄音</button>
        <button id="clearButton">清除內容</button>
    </div>
    <div id="status">準備就緒</div>
    <div class="output-container">
        <div class="output-box">
            <div class="output-label">原始文字</div>
            <div id="output"></div>
        </div>
        <div class="output-box">
            <div class="output-label">中文翻譯</div>
            <div id="translation"></div>
        </div>
    </div>

    <script>
        const languageSelect = document.getElementById('languageSelect');
        const startButton = document.getElementById('startButton');
        const stopButton = document.getElementById('stopButton');
        const clearButton = document.getElementById('clearButton');
        const status = document.getElementById('status');
        const output = document.getElementById('output');
        const translation = document.getElementById('translation');

        let allTranscripts = '';
        let allTranslations = '';

        // 發送文字到 Python 後端進行翻譯
        async function sendForTranslation(text, sourceLang) {
            try {
                const response = await fetch('/translate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        sourceLang: sourceLang
                    })
                });
                const data = await response.json();
                return data.translation;
            } catch (error) {
                console.error('翻譯請求錯誤:', error);
                return '翻譯錯誤';
            }
        }

        if (!('webkitSpeechRecognition' in window)) {
            alert('您的瀏覽器不支援語音辨識功能，請使用 Chrome 瀏覽器。');
        }

        const recognition = new webkitSpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;

        startButton.addEventListener('click', () => {
            recognition.lang = languageSelect.value;
            recognition.start();
            startButton.disabled = true;
            stopButton.disabled = false;
            status.textContent = '正在聆聽...';
        });

        stopButton.addEventListener('click', () => {
            recognition.stop();
            startButton.disabled = false;
            stopButton.disabled = true;
            status.textContent = '已停止';
        });

        clearButton.addEventListener('click', () => {
            allTranscripts = '';
            allTranslations = '';
            output.innerHTML = '';
            translation.innerHTML = '';
            status.textContent = '內容已清除';
        });

        recognition.onresult = async (event) => {
            let interimTranscript = '';
            let finalTranscriptForThisResult = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscriptForThisResult += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            if (finalTranscriptForThisResult) {
                allTranscripts += (allTranscripts ? '\\n' : '') + finalTranscriptForThisResult;

                // 發送到 Python 後端進行翻譯
                const translatedText = await sendForTranslation(
                    finalTranscriptForThisResult,
                    languageSelect.value
                );
                allTranslations += (allTranslations ? '\\n' : '') + translatedText;
            }

            // 更新顯示
            output.innerHTML = `
                <div style="color: #000">${allTranscripts}</div>
                ${interimTranscript ? `<div style="color: #666">${interimTranscript}</div>` : ''}
            `;

            translation.innerHTML = `
                <div style="color: #000">${allTranslations}</div>
            `;
        };

        recognition.onerror = (event) => {
            status.textContent = '發生錯誤: ' + event.error;
            startButton.disabled = false;
            stopButton.disabled = true;
        };

        recognition.onend = () => {
            status.textContent = '語音辨識已結束';
            startButton.disabled = false;
            stopButton.disabled = true;
        };
    </script>
</body>
</html>
    """

# --------------------------------------------------
# 2. 翻譯 API
# --------------------------------------------------
@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text', '')
    source_lang = data.get('sourceLang', '')

    # 針對不同的語言可自由客製化，以下僅做示範。
    if source_lang == 'en-US':
        lang_hint = "English"
    elif source_lang == 'yue-Hant-HK':
        lang_hint = "Cantonese"
    elif source_lang == 'zh-TW':
        lang_hint = "Chinese"
    else:
        lang_hint = "Unknown language"

    prompt = (
        f"Please translate the following {lang_hint} text into Traditional Chinese:\n\n"
        f"{text}"
    )

    try:
        response = model.generate_content(prompt)
        translation = response.text.strip()
    except Exception as e:
        print("Error during translation:", e)
        translation = "翻譯發生錯誤，請稍後再試。"

    return jsonify({'translation': translation})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
