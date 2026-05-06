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
                return record
            return {"votes": {}, "last_updated": ""}
    except Exception as e:
        pass
    return {"votes": {}, "last_updated": ""}


def save_to_cloud(data):
    """保存投票数据到JSONBin"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
        headers = {
            "Content-Type": "application/json",
            "X-Master-Key": JSONBIN_API_KEY
        }
        data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = requests.put(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        return False


def sync_data():
    """从云端同步数据到本地session"""
    cloud_data = load_from_cloud()
    if "votes" in cloud_data:
        st.session_state.votes = cloud_data["votes"]
    else:
        st.session_state.votes = {}
    return cloud_data


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


def local_analysis(topic, counts, total_votes):
    """本地规则分析（备用）"""
    if total_votes == 0:
        return "还没有投票数据~"
    max_opt = max(counts, key=counts.get)
    max_votes = counts[max_opt]
    min_opt = min(counts, key=counts.get)
    min_votes = counts[min_opt]
    max_percent = round(max_votes / total_votes * 100, 1)
    
    analysis = f"📊 最受欢迎的是「{max_opt}」，获得 {max_votes} 票，占 {max_percent}%。\n"
    analysis += f"🥉 得票最少的是「{min_opt}」，获得 {min_votes} 票。"
    return analysis


# ========== 页面配置 ==========
st.set_page_config(page_title="班级投票系统 - 多设备同步版", layout="wide")

# 初始化：从云端加载数据
if 'votes' not in st.session_state:
    sync_data()
if 'last_vote_code' not in st.session_state:
    st.session_state.last_vote_code = None


# ========== 侧边栏 ==========
with st.sidebar:
    st.header("⚙️ 系统状态")
    
    if DEEPSEEK_API_KEY:
        st.success("✅ AI大模型已就绪")
    
    # 显示当前投票数量
    st.info(f"📋 当前共有 {len(st.session_state.votes)} 场投票")
    
    st.markdown("---")
    st.header("👩‍🏫 教师控制台")
    
    topic = st.text_input("📝 投票主题", "最喜欢的科目")
    options_text = st.text_area("📋 选项（每行一个）", "语文\n数学\n英语\n体育\n道法\n科学\n音乐\n美术", height=120)
    
    # 生成投票按钮
    if st.button("✅ 生成新投票", use_container_width=True, type="primary"):
        option_list = [opt.strip() for opt in options_text.split("\n") if opt.strip()]
        if len(option_list) < 2:
            st.error("至少需要2个选项")
        else:
            # 生成6位投票码
            vote_code = str(random.randint(100000, 999999))
            # 确保投票码不重复
            while vote_code in st.session_state.votes:
                vote_code = str(random.randint(100000, 999999))
            
            # 创建新投票
            st.session_state.votes[vote_code] = {
                "topic": topic,
                "options": option_list,
                "counts": {opt: 0 for opt in option_list},
                "total_votes": 0,
                "created_at": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state.last_vote_code = vote_code
            
            # 保存到云端
            if save_to_cloud({"votes": st.session_state.votes}):
                st.session_state.sync_status = f"✅ 投票 {vote_code} 已创建"
                # 使用大号字体显示投票码
                st.markdown(f"""
                <div style="background-color:#d4edda; padding:20px; border-radius:10px; text-align:center; margin:10px 0;">
                    <p style="font-size:16px; margin:0;">✅ 投票已创建！</p>
                    <p style="font-size:48px; font-weight:bold; margin:10px 0; color:#155724;">{vote_code}</p>
                    <p style="font-size:14px; margin:0;">请将此6位码告诉学生</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("保存失败，请检查网络连接")
    
    st.markdown("---")
    
    if st.button("🗑️ 清除所有投票", use_container_width=True):
        st.session_state.votes = {}
        st.session_state.last_vote_code = None
        save_to_cloud({"votes": {}})
        st.success("✅ 已清除所有投票")
        st.rerun()
    
    # 手动同步按钮
    if st.button("🔄 手动同步数据", use_container_width=True):
        sync_data()
        st.success(f"✅ 已同步，共 {len(st.session_state.votes)} 场投票")
        st.rerun()


# ========== 主区域 ==========
st.title("📊 班级投票实时统计看板")
st.caption("💡 手机、电脑数据实时同步 | 所有设备共享同一投票池")

# 显示最后创建的投票码（醒目提示）
if st.session_state.last_vote_code:
    last_code = st.session_state.last_vote_code
    if last_code in st.session_state.votes:
        st.success(f"🎯 **最新投票码：{last_code}** - {st.session_state.votes[last_code]['topic']}")


# ========== 学生投票区 ==========
st.subheader("🎯 学生投票区")

# 使用两列布局，让输入更醒目
col_code, col_btn = st.columns([3, 1])
with col_code:
    vote_code_input = st.text_input("请输入6位投票码", placeholder="例如：475772", label_visibility="collapsed")
with col_btn:
    st.write("")
    st.write("")
    search_btn = st.button("🔍 查询投票", use_container_width=True)

# 处理查询
if search_btn and vote_code_input:
    if vote_code_input in st.session_state.votes:
        st.session_state.current_vote = vote_code_input
        st.rerun()
    else:
        st.error(f"❌ 投票码 {vote_code_input} 不存在，请检查后重新输入")

# 显示当前投票
current_vote = st.session_state.get('current_vote', None)
if current_vote and current_vote in st.session_state.votes:
    vdata = st.session_state.votes[current_vote]
    
    st.markdown(f"""
    <div style="background-color:#e8f4f8; padding:15px; border-radius:10px; margin:10px 0;">
        <h3 style="margin:0; text-align:center;">📌 {vdata['topic']}</h3>
        <p style="text-align:center; margin:5px 0 0 0; font-size:12px;">创建于 {vdata.get('created_at', '未知')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 检查是否已投票
    voter_key = f"voted_{current_vote}"
    if voter_key not in st.session_state:
        st.session_state[voter_key] = False
    
    if st.session_state[voter_key]:
        st.warning("✅ 您已经投过票了！感谢参与~")
    else:
        choice = st.radio("请选择一项：", vdata["options"], index=None, horizontal=True)
        if st.button("📮 提交投票", type="primary", use_container_width=True):
            if choice:
                vdata["counts"][choice] += 1
                vdata["total_votes"] += 1
                st.session_state[voter_key] = True
                # 保存到云端
                if save_to_cloud({"votes": st.session_state.votes}):
                    st.success("🎉 投票成功！数据已同步")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("保存失败，请重试")
            else:
                st.error("请先选择一个选项")
    
    # 显示结果
    st.markdown("---")
    st.subheader("📈 实时统计结果")
    
    df = pd.DataFrame({"选项": list(vdata["counts"].keys()), "票数": list(vdata["counts"].values())})
    df = df.sort_values("票数", ascending=False)
    
    col1, col2 = st.columns(2)
    with col1:
        if df["票数"].sum() > 0:
            fig_bar = px.bar(df, x="选项", y="票数", title="条形图", text="票数", color="票数", color_continuous_scale="Blues")
            fig_bar.update_traces(textposition="outside")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("📊 投票后将显示条形图")
    
    with col2:
        if df["票数"].sum() > 0:
            fig_pie = px.pie(df, names="选项", values="票数", title="饼图", hole=0.4)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("🥧 投票后将显示饼图")
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("📊 总投票人数", vdata["total_votes"])
    
    # AI解读
    st.markdown("---")
    st.subheader("🤖 AI智能解读")
    if vdata["total_votes"] > 0:
        if st.button("🔍 生成AI解读", type="secondary"):
            with st.spinner("🤖 AI正在分析投票结果..."):
                analysis = call_deepseek_analysis(vdata["topic"], vdata["counts"], vdata["total_votes"])
                if analysis is None:
                    analysis = local_analysis(vdata["topic"], vdata["counts"], vdata["total_votes"])
                st.success(analysis)
    else:
        st.info("💡 投票开始后，点击这里查看AI解读")
    
    # 返回按钮
    if st.button("← 返回查询其他投票"):
        st.session_state.current_vote = None
        st.rerun()

elif vote_code_input and not search_btn:
    st.info("💡 输入投票码后，点击「查询投票」按钮")


# ========== 教师工具：查看所有投票 ==========
with st.expander("📋 教师工具：查看所有投票记录"):
    if st.session_state.votes:
        for code, info in st.session_state.votes.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{code}** - {info['topic']} | 共{info['total_votes']}人参与")
            with col2:
                if st.button(f"使用", key=f"use_{code}"):
                    st.session_state.current_vote = code
                    st.rerun()
            for opt, cnt in info['counts'].items():
                st.write(f"  - {opt}: {cnt}票")
            st.markdown("---")
    else:
        st.write("暂无投票，请先在左侧创建")


# ========== 页脚 ==========
st.markdown("---")
st.caption("🎓 小学数学教学专用 | 数据存储于JSONBin | 支持多设备实时同步")
