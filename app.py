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

# 教师密码（可以修改成你想要的密码）
TEACHER_PASSWORD = "teacher2026"  # ⬅️ 修改这里设置教师密码
# ======================================================


# ========== JSONBin云存储函数 ==========
def load_from_cloud():
    """从JSONBin加载投票数据"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
        headers = {"X-Master-Key": JSONBIN_API_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            record = data.get("record", {})
            if isinstance(record, dict):
                return record.get("votes", {})
    except Exception as e:
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
        response = requests.put(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        return False


def sync_from_cloud():
    """从云端同步数据到本地（智能合并，取最大票数）"""
    cloud_votes = load_from_cloud()
    if cloud_votes:
        for code, cloud_data in cloud_votes.items():
            if code in st.session_state.votes:
                local_counts = st.session_state.votes[code]["counts"]
                cloud_counts = cloud_data["counts"]
                for opt in cloud_counts:
                    if cloud_counts[opt] > local_counts.get(opt, 0):
                        local_counts[opt] = cloud_counts[opt]
                st.session_state.votes[code]["counts"] = local_counts
                st.session_state.votes[code]["total_votes"] = sum(local_counts.values())
            else:
                st.session_state.votes[code] = cloud_data
        save_to_cloud(st.session_state.votes)
    return len(cloud_votes)


def force_sync_to_cloud():
    """强制将本地数据同步到云端"""
    return save_to_cloud(st.session_state.votes)


# ========== AI分析函数 ==========
def call_deepseek_analysis(topic, counts, total_votes):
    """调用DeepSeek API分析投票结果"""
    if not DEEPSEEK_API_KEY:
        return None
    
    max_option = max(counts, key=counts.get)
    
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

# 初始化session状态
if 'votes' not in st.session_state:
    cloud_votes = load_from_cloud()
    st.session_state.votes = cloud_votes if cloud_votes else {}
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
if 'teacher_authenticated' not in st.session_state:
    st.session_state.teacher_authenticated = False


# ========== 教师登录验证函数 ==========
def teacher_login():
    """显示教师登录界面"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔐 教师专区")
    
    password = st.sidebar.text_input("请输入教师密码", type="password", key="teacher_password")
    
    if st.sidebar.button("登录", use_container_width=True):
        if password == TEACHER_PASSWORD:
            st.session_state.teacher_authenticated = True
            st.sidebar.success("登录成功！")
            st.rerun()
        else:
            st.sidebar.error("密码错误！")
    
    st.sidebar.info("💡 学生无需密码，直接使用下方投票区")


# ========== 教师控制台（需要登录） ==========
def teacher_console():
    """教师控制台内容"""
    with st.sidebar:
        st.header("👩‍🏫 教师控制台")
        
        # 显示同步状态
        total_votes_count = sum(info.get('total_votes', 0) for info in st.session_state.votes.values())
        st.caption(f"☁️ 云端已连接 | {len(st.session_state.votes)} 场投票 | 共 {total_votes_count} 人次")
        st.caption(f"📅 最后同步: {st.session_state.last_sync}")
        
        st.markdown("---")
        
        topic = st.text_input("📝 投票主题", "最喜欢的季节")
        options_text = st.text_area("📋 选项（每行一个）", "春季\n夏季\n秋季\n冬季", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 生成新投票", use_container_width=True):
                option_list = [opt.strip() for opt in options_text.split("\n") if opt.strip()]
                if len(option_list) < 2:
                    st.error("至少需要2个选项")
                else:
                    vote_code = str(random.randint(100000, 999999))
                    while vote_code in st.session_state.votes:
                        vote_code = str(random.randint(100000, 999999))
                    
                    st.session_state.votes[vote_code] = {
                        "topic": topic,
                        "options": option_list,
                        "counts": {opt: 0 for opt in option_list},
                        "total_votes": 0,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    if force_sync_to_cloud():
                        st.success(f"✅ 投票已创建！\n\n**投票码：{vote_code}**")
                        st.balloons()
                    else:
                        st.error("保存失败，请检查网络")
        
        with col2:
            if st.button("🔄 同步数据", use_container_width=True):
                with st.spinner("同步中..."):
                    sync_from_cloud()
                    st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
                    st.success("同步完成！")
                    st.rerun()
        
        st.markdown("---")
        
        if st.button("🗑️ 清除所有投票", use_container_width=True):
            st.session_state.votes = {}
            if force_sync_to_cloud():
                st.success("✅ 已清除所有投票")
                st.rerun()
            else:
                st.error("清除失败")
        
        # 登出按钮
        st.markdown("---")
        if st.button("🚪 退出教师模式", use_container_width=True):
            st.session_state.teacher_authenticated = False
            st.rerun()


# ========== 页面主体 ==========
st.title("📊 班级投票实时统计看板")
st.caption("💡 输入投票码参与投票 | 教师请点击左侧登录")

# 侧边栏：判断是否显示教师控制台
if st.session_state.teacher_authenticated:
    teacher_console()
else:
    teacher_login()


# ========== 学生投票区（所有用户可见） ==========
st.subheader("🎯 学生投票区")
vote_code_input = st.text_input("请输入6位投票码", placeholder="例如: 475772")

if vote_code_input and vote_code_input in st.session_state.votes:
    vdata = st.session_state.votes[vote_code_input]
    st.markdown(f"### 📌 {vdata['topic']}")
    
    # 检查是否已投票
    voter_key = f"voted_{vote_code_input}"
    if voter_key not in st.session_state:
        st.session_state[voter_key] = False
    
    if st.session_state[voter_key]:
        st.warning("✅ 您已经投过票了！")
    else:
        choice = st.radio("请选择一项：", vdata["options"], index=None, horizontal=True)
        if st.button("📮 提交投票", type="primary"):
            if choice:
                sync_from_cloud()
                vdata = st.session_state.votes[vote_code_input]
                vdata["counts"][choice] += 1
                vdata["total_votes"] += 1
                st.session_state.votes[vote_code_input] = vdata
                st.session_state[voter_key] = True
                
                if force_sync_to_cloud():
                    st.success("🎉 投票成功！")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("保存失败，请重试")
            else:
                st.error("请先选择一个选项")
    
    # 显示统计结果
    st.markdown("---")
    st.subheader("📈 实时统计结果")
    
    df = pd.DataFrame({
        "选项": list(vdata["counts"].keys()),
        "票数": list(vdata["counts"].values())
    })
    df = df.sort_values("票数", ascending=False)
    
    col1, col2 = st.columns(2)
    with col1:
        if df["票数"].sum() > 0:
            fig_bar = px.bar(df, x="选项", y="票数", title="条形图", text="票数", color="票数")
            fig_bar.update_traces(textposition="outside")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("📊 投票后将显示条形图")
    
    with col2:
        if df["票数"].sum() > 0:
            fig_pie = px.pie(df, names="选项", values="票数", title="饼图")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("🥧 投票后将显示饼图")
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"总投票人数：{vdata['total_votes']} 人")
    
    # AI分析（仅教师登录后可见？不，学生也可以看分析结果）
    if st.button("🤖 AI智能分析"):
        with st.spinner("AI正在分析中..."):
            if vdata['total_votes'] > 0:
                analysis = call_deepseek_analysis(vdata["topic"], vdata["counts"], vdata["total_votes"])
                if analysis:
                    st.success(analysis)
                else:
                    max_opt = max(vdata["counts"], key=vdata["counts"].get)
                    max_votes = vdata["counts"][max_opt]
                    percent = max_votes / vdata['total_votes'] * 100
                    st.info(f"🎉 最受欢迎的是「{max_opt}」，获得 {max_votes} 票，占比 {percent:.1f}%。")
            else:
                st.info("还没有投票数据~")

elif vote_code_input:
    st.error("❌ 投票码不存在，请检查后重新输入")
else:
    st.info("💡 请输入教师给出的6位投票码开始投票")

# ========== 历史投票记录（默认收起，所有人可见） ==========
with st.expander("📚 历史投票记录（点击展开查看）"):
    if st.session_state.votes:
        sorted_votes = sorted(st.session_state.votes.items(), 
                            key=lambda x: x[1].get('created_at', ''), 
                            reverse=True)
        
        for code, info in sorted_votes:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{code}**")
                with col2:
                    st.write(f"{info['topic']}")
                with col3:
                    st.write(f"共 {info['total_votes']} 人")
                
                if info['total_votes'] > 0:
                    df_history = pd.DataFrame({
                        "选项": list(info["counts"].keys()),
                        "票数": list(info["counts"].values())
                    })
                    df_history = df_history.sort_values("票数", ascending=False)
                    if df_history["票数"].sum() > 0:
                        df_history["占比"] = (df_history["票数"] / df_history["票数"].sum() * 100).round(1).astype(str) + "%"
                    st.dataframe(df_history, use_container_width=True, hide_index=True)
                else:
                    st.caption("暂无投票数据")
                st.markdown("---")
    else:
        st.info("暂无投票记录")

# 页脚
st.markdown("---")
st.caption("🎓 小学数学教学专用 | 数据存储于JSONBin | 支持多设备实时同步")
