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
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            record = data.get("record", {})
            if isinstance(record, dict):
                return record.get("votes", {})
    except Exception as e:
        st.sidebar.error(f"加载失败：{str(e)[:50]}")
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
        st.sidebar.error(f"保存失败：{str(e)[:50]}")
        return False


def sync_from_cloud():
    """从云端同步数据到本地"""
    cloud_votes = load_from_cloud()
    if cloud_votes:
        # 合并云端数据到本地（云端优先）
        for code, cloud_data in cloud_votes.items():
            if code in st.session_state.votes:
                # 如果本地已有，比较票数，取最大值（防止覆盖）
                local_counts = st.session_state.votes[code]["counts"]
                cloud_counts = cloud_data["counts"]
                for opt in cloud_counts:
                    if cloud_counts[opt] > local_counts.get(opt, 0):
                        local_counts[opt] = cloud_counts[opt]
                st.session_state.votes[code]["counts"] = local_counts
                st.session_state.votes[code]["total_votes"] = sum(local_counts.values())
            else:
                # 本地没有，直接添加
                st.session_state.votes[code] = cloud_data
    return len(cloud_votes)


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

# 初始化session状态
if 'votes' not in st.session_state:
    cloud_votes = load_from_cloud()
    st.session_state.votes = cloud_votes if cloud_votes else {}
if 'vote_records' not in st.session_state:
    st.session_state.vote_records = {}
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")

st.title("📊 班级投票实时统计看板")

# 侧边栏：教师控制台
with st.sidebar:
    st.header("👩‍🏫 教师控制台")
    
    # 显示同步状态
    total_votes_count = sum(info.get('total_votes', 0) for info in st.session_state.votes.values())
    st.caption(f"☁️ 云端已同步 | {len(st.session_state.votes)} 场投票 | 共 {total_votes_count} 人次")
    st.caption(f"📅 最后同步: {st.session_state.last_sync}")
    
    topic = st.text_input("投票主题", "最喜欢的运动")
    options_text = st.text_area("选项（每行一个）", "篮球\n足球\n乒乓球\n跳绳")
    
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
                    "total_votes": 0
                }
                
                if save_to_cloud(st.session_state.votes):
                    st.success(f"✅ 投票已创建！\n\n**投票码：{vote_code}**")
                    st.balloons()
                else:
                    st.error("保存失败，请检查网络")
    
    with col2:
        if st.button("🔄 同步数据", use_container_width=True):
            with st.spinner("同步中..."):
                count = sync_from_cloud()
                st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
                st.success(f"同步完成！更新了 {count} 场投票")
                st.rerun()

# 主体区域：学生投票
st.subheader("🎯 学生投票区")
vote_code_input = st.text_input("请输入6位投票码", placeholder="例如: 475772")

if vote_code_input and vote_code_input in st.session_state.votes:
    vdata = st.session_state.votes[vote_code_input]
    st.markdown(f"### 📌 {vdata['topic']}")
    
    # 检查是否已投票（基于浏览器session）
    voter_key = f"voted_{vote_code_input}"
    if voter_key not in st.session_state:
        st.session_state[voter_key] = False
    
    if st.session_state[voter_key]:
        st.warning("✅ 您已经投过票了！")
    else:
        choice = st.radio("请选择一项：", vdata["options"], index=None, horizontal=True)
        if st.button("📮 提交投票", type="primary"):
            if choice:
                # 更新本地数据
                vdata["counts"][choice] += 1
                vdata["total_votes"] += 1
                st.session_state[voter_key] = True
                
                # 保存到云端
                if save_to_cloud(st.session_state.votes):
                    st.success("🎉 投票成功！数据已同步到云端")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("保存失败，请重试")
            else:
                st.error("请先选择一个选项")
    
    st.markdown("---")
    st.subheader("📈 实时统计结果")
    
    df = pd.DataFrame({
        "选项": list(vdata["counts"].keys()),
        "票数": list(vdata["counts"].values())
    })
    df = df.sort_values("票数", ascending=False)
    
    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(df, x="选项", y="票数", title=f"条形图 - {vdata['topic']}", text="票数", color="票数")
        fig_bar.update_traces(textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        if df["票数"].sum() > 0:
            fig_pie = px.pie(df, names="选项", values="票数", title=f"饼图 - {vdata['topic']}")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("投票后将显示饼图")
    
    # 详细统计表格
    st.subheader("📋 详细投票分布")
    df_display = df.copy()
    df_display["占比"] = (df_display["票数"] / df_display["票数"].sum() * 100).round(1).astype(str) + "%"
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.caption(f"总投票人数：{vdata['total_votes']} 人")
    
    # AI智能分析
    if st.button("🤖 AI智能分析"):
        with st.spinner("AI正在分析中..."):
            if vdata['total_votes'] > 0:
                analysis = call_deepseek_analysis(vdata["topic"], vdata["counts"], vdata["total_votes"])
                if analysis:
                    st.success(analysis)
                else:
                    # 备用本地分析
                    max_opt = max(vdata["counts"], key=vdata["counts"].get)
                    max_votes = vdata["counts"][max_opt]
                    percent = max_votes / vdata['total_votes'] * 100
                    analysis = f"🎉 最受欢迎的是「{max_opt}」，获得 {max_votes} 票，占比 {percent:.1f}%。"
                    if percent > 50:
                        analysis += " 超过半数同学选择，很受欢迎！"
                    else:
                        analysis += " 其他选项也有较多支持。"
                    st.info(analysis)
            else:
                st.info("还没有投票数据，请等待同学参与~")

elif vote_code_input:
    st.error("❌ 投票码不存在，请检查后重新输入")
else:
    st.info("💡 教师先在左侧创建投票，然后将6位投票码告诉学生")

# 查看所有投票详细分布（新增功能）
st.markdown("---")
st.subheader("📊 查看所有投票详细分布")

if st.session_state.votes:
    # 选择要查看的投票
    vote_options = {code: f"{code} - {info['topic']} (共{info['total_votes']}人)" 
                    for code, info in st.session_state.votes.items()}
    selected_vote = st.selectbox("选择要查看的投票", list(vote_options.keys()), format_func=lambda x: vote_options[x])
    
    if selected_vote:
        vdata = st.session_state.votes[selected_vote]
        st.markdown(f"### 📌 {vdata['topic']}")
        
        # 显示详细分布
        df_detail = pd.DataFrame({
            "选项": list(vdata["counts"].keys()),
            "票数": list(vdata["counts"].values())
        })
        df_detail = df_detail.sort_values("票数", ascending=False)
        df_detail["占比"] = (df_detail["票数"] / df_detail["票数"].sum() * 100).round(1).astype(str) + "%"
        df_detail["排名"] = range(1, len(df_detail) + 1)
        
        # 重新排列列顺序
        df_detail = df_detail[["排名", "选项", "票数", "占比"]]
        st.dataframe(df_detail, use_container_width=True, hide_index=True)
        
        # 显示柱状图
        fig_detail = px.bar(df_detail, x="选项", y="票数", title=f"{vdata['topic']} - 投票分布", 
                            text="票数", color="票数", color_continuous_scale="Viridis")
        fig_detail.update_traces(textposition="outside")
        st.plotly_chart(fig_detail, use_container_width=True)
        
        st.caption(f"📅 创建时间: {vdata.get('created_at', '未知')} | 总参与人数: {vdata['total_votes']}")
else:
    st.info("暂无投票，请先在左侧创建")

# 页脚
st.markdown("---")
st.caption("🎓 小学数学教学专用 | 数据存储于JSONBin | 支持多设备实时同步")
