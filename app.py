import streamlit as st
import pandas as pd
import plotly.express as px
import random
import requests
import json
from datetime import datetime

# ==================== 您的配置信息 ====================
DEEPSEEK_API_KEY = "sk-e4818962b72f481984bc5f94e9bf8778"
JSONBIN_BIN_ID = "69fb608236566621a8315f1d"
JSONBIN_API_KEY = "$2a$10$9oM8sPqbAk2HSirWzg20JOrJtQ3FpZ3DP4rYlp9Je9RaNTm7n7UUe"
# ======================================================


# ========== JSONBin云存储函数 ==========
def load_from_cloud():
    """从JSONBin加载投票数据"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
        headers = {"X-Master-Key": JSONBIN_API_KEY}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            record = data.get("record", {})
            if isinstance(record, dict):
                return record.get("votes", {})
    except:
        pass
    return {}


def save_to_cloud(votes_data):
    """保存投票数据到JSONBin"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
        headers = {
            "Content-Type": "application/json",
            "X-Master-Key": JSONBIN_API_KEY
        }
        data = {
            "votes": votes_data,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        response = requests.put(url, headers=headers, json=data, timeout=5)
        return response.status_code == 200
    except:
        return False


# ========== AI分析函数 ==========
def call_deepseek_analysis(topic, counts, total_votes):
    """调用DeepSeek API分析投票结果"""
    if not DEEPSEEK_API_KEY:
        return None
    
    max_option = max(counts, key=counts.get)
    max_votes = counts[max_option]
    
    system_prompt = """你是一位亲切的小学数学老师，正在给三年级学生讲解数据的收集与整理。
请用活泼、鼓励的语气解读投票结果。要求：先说最受欢迎的结果和票数，再说最少被选的结果，最后给出一条教学建议。总字数150字以内。"""
    
    user_prompt = f"投票主题：{topic}，各选项票数：{dict(counts)}，总投票人数：{total_votes}人"
    
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None


# ========== 页面配置 ==========
st.set_page_config(page_title="班级投票系统", layout="wide")

# 初始化session状态：从云端加载数据
if 'votes' not in st.session_state:
    cloud_votes = load_from_cloud()
    st.session_state.votes = cloud_votes
if 'vote_records' not in st.session_state:
    st.session_state.vote_records = {}

st.title("📊 班级投票实时统计看板")

# 侧边栏：教师控制台
with st.sidebar:
    st.header("👩‍🏫 教师控制台")
    
    # 显示同步状态
    st.caption(f"☁️ 云端已同步 | {len(st.session_state.votes)} 场投票")
    
    topic = st.text_input("投票主题", "最喜欢的运动")
    options_text = st.text_area("选项（每行一个）", "篮球\n足球\n乒乓球\n跳绳")
    
    if st.button("✅ 生成新投票", use_container_width=True):
        option_list = [opt.strip() for opt in options_text.split("\n") if opt.strip()]
        if len(option_list) < 2:
            st.error("至少需要2个选项")
        else:
            vote_code = str(random.randint(100000, 999999))
            # 确保投票码不重复
            while vote_code in st.session_state.votes:
                vote_code = str(random.randint(100000, 999999))
            
            st.session_state.votes[vote_code] = {
                "topic": topic,
                "options": option_list,
                "counts": {opt: 0 for opt in option_list},
                "total_votes": 0
            }
            st.session_state.vote_records[vote_code] = set()
            
            # 保存到云端
            if save_to_cloud(st.session_state.votes):
                st.success(f"✅ 投票已创建！\n\n**投票码：{vote_code}**")
                st.info("学生访问此网址后输入投票码即可投票")
            else:
                st.error("保存失败，请检查网络")
    
    if st.button("🔄 手动同步", use_container_width=True):
        cloud_votes = load_from_cloud()
        st.session_state.votes = cloud_votes
        st.success(f"同步完成，共 {len(st.session_state.votes)} 场投票")
        st.rerun()

# 主体区域：学生投票
st.subheader("🎯 学生投票区")
vote_code_input = st.text_input("请输入6位投票码")

if vote_code_input and vote_code_input in st.session_state.votes:
    vdata = st.session_state.votes[vote_code_input]
    st.markdown(f"### {vdata['topic']}")
    
    if f"voted_{vote_code_input}" not in st.session_state:
        st.session_state[f"voted_{vote_code_input}"] = False
    
    if st.session_state[f"voted_{vote_code_input}"]:
        st.warning("✅ 您已经投过票了！")
    else:
        choice = st.radio("请选择一项：", vdata["options"], index=None)
        if st.button("📮 提交投票", type="primary"):
            if choice:
                vdata["counts"][choice] += 1
                vdata["total_votes"] += 1
                st.session_state[f"voted_{vote_code_input}"] = True
                
                # 保存到云端
                save_to_cloud(st.session_state.votes)
                
                st.success("🎉 投票成功！谢谢参与")
                st.rerun()
            else:
                st.error("请先选择一个选项")
    
    st.markdown("---")
    st.subheader("📈 实时统计结果")
    
    df = pd.DataFrame({
        "选项": list(vdata["counts"].keys()),
        "票数": list(vdata["counts"].values())
    })
    
    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(df, x="选项", y="票数", title=f"条形图 - {vdata['topic']}", text="票数")
        fig_bar.update_traces(textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        fig_pie = px.pie(df, names="选项", values="票数", title=f"饼图 - {vdata['topic']}")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    st.dataframe(df, use_container_width=True)
    st.caption(f"总投票人数：{vdata['total_votes']} 人")
    
    # AI智能分析（调用DeepSeek）
    if st.button("🤖 AI智能分析"):
        with st.spinner("AI正在分析中..."):
            if vdata['total_votes'] > 0:
                # 优先使用DeepSeek API
                analysis = call_deepseek_analysis(vdata["topic"], vdata["counts"], vdata["total_votes"])
                if analysis:
                    st.info(analysis)
                else:
                    # 备用本地分析
                    max_opt = max(vdata["counts"], key=vdata["counts"].get)
                    max_votes = vdata["counts"][max_opt]
                    percent = max_votes / vdata['total_votes'] * 100
                    analysis = f"🎉 分析结果：最受欢迎的是「{max_opt}」，获得 {max_votes} 票，占比 {percent:.1f}%。"
                    if percent > 50:
                        analysis += " 超过半数同学选择，很受欢迎！"
                    else:
                        analysis += " 其他选项也有较多支持，可以再听听大家的意见。"
                    st.info(analysis)
            else:
                st.info("还没有投票数据，请等待同学参与~")

elif vote_code_input:
    st.error("❌ 投票码不存在，请检查后重新输入")
else:
    st.info("请输入教师给出的6位投票码开始投票")

with st.expander("📋 教师工具：查看所有投票"):
    if st.session_state.votes:
        for code, info in st.session_state.votes.items():
            st.write(f"**{code}** - {info['topic']} (共{info['total_votes']}票)")
    else:
        st.write("暂无投票")
