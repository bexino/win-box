import json
import genanki

# 1. 定义 Anki 模板（HTML/CSS 布局）
word_model = genanki.Model(
    1842938472,  # 随机生成一个唯一ID
    'IELTS_Json_Model',
    fields=[
        {'name': 'Word'},       # 单词
        {'name': 'Phonetic'},   # 音标
        {'name': 'Meaning'},    # 释义
        {'name': 'Memory'},     # 记忆法
        {'name': 'Examples'}    # 例句
    ],
    templates=[
        {
            'name': 'Card 1',
            'qfmt': '<div style="font-size: 40px; font-weight: bold; text-align: center; margin-top: 50px;">{{Word}}</div>',
            'afmt': '''
                {{FrontSide}}
                <hr id="answer">
                <div style="font-size: 16px; color: #666; text-align: center; margin-bottom: 15px;">[{{Phonetic}}]</div>
                
                <div style="background: #f4f6f9; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <b style="color: #0056b3;">释义：</b><br>{{Meaning}}
                </div>
                
                {{#Memory}}
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #ffc107;">
                    <b style="color: #856404;">💡 记忆方法：</b><br>{{Memory}}
                </div>
                {{/Memory}}
                
                {{#Examples}}
                <div style="background: #e2f0d9; padding: 15px; border-radius: 8px;">
                    <b style="color: #385723;">📝 例句：</b><br>{{Examples}}
                </div>
                {{/Examples}}
            ''',
        },
    ],
    css='body { font-family: sans-serif; font-size: 18px; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }'
)

# 2. 创建 Anki 牌组
my_deck = genanki.Deck(2847192847, '词汇书')

# 3. 逐行读取你的 JSONL 词书文件并解析
with open('IELTS_2.json', 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            data = json.loads(line.strip())
            word_info = data['content']['word']
            inner_content = word_info['content']
            
            # 提取字段
            word = data.get('headWord', '')
            # 组合英美音标
            us_p = inner_content.get('usphone', '')
            uk_p = inner_content.get('ukphone', '')
            phonetic = f"美: /{us_p}/  英: /{uk_p}/" if us_p or uk_p else ""
            
            # 提取释义
            meaning_list = []
            for t in inner_content.get('trans', []):
                pos = t.get('pos', '')
                tran_cn = t.get('tranCn', '')
                meaning_list.append(f"<b>[{pos}.]</b> {tran_cn}")
            meaning = "<br>".join(meaning_list)
            
            # 提取记忆法
            memory = inner_content.get('remMethod', {}).get('val', '')
            
            # 提取例句 (转换为 HTML 换行格式)
            example_list = []
            sentences = inner_content.get('sentence', {}).get('sentences', [])
            for s in sentences:
                eng = s.get('sContent', '')
                cn = s.get('sCn', '')
                example_list.append(f"• {eng}<br><span style='color: #666; font-size: 16px;'>{cn}</span>")
            examples = "<br><br>".join(example_list)
            
            # 生成卡片并加入 Deck
            note = genanki.Note(
                model=word_model,
                fields=[word, phonetic, meaning, memory, examples]
            )
            my_deck.add_note(note)
            
        except Exception as e:
            print(f"解析第 {line_num} 行时遇到一点问题，已跳过。错误原因: {e}")

# 4. 打包导出为可在 Anki 中直接双击打开的包文件
genanki.Package(my_deck).write_to_file('output_Anki.apkg')
print("转换成功！已为您生成 'output_Anki.apkg' 文件。")