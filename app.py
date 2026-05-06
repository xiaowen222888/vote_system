import streamlit as st
import pandas as pd
import plotly.express as px
import random
import requests
import json
import re

DEEPSEEK_API_KEY = "sk-e4818962b72f481984bc5f94e9bf8778"  

# ========== 页面配置 ==========
st.set_page_config(
    page_title="班级投票系统 - AI智能版",
    page_icon="📊",
    layout="wide"
)

# ========== 初始化Session状态 ==========
if 'votes' not in st.session_state:
    st.session_state.votes = {}
if 'vote_records' not in st.session_state:
    st.session_state.vote_records = {}


# ========== 辅助函数：调用DeepSeek API ==========
def call_deepseek_analysis(topic, counts, total_votes):
    """
    调用DeepSeek API分析投票结果
    """
    global DEEPSEEK_API_KEY
    
    # 如果没有配置API Key，直接返回None，使用本地分析
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_API_KEY_HERE":
        return None
    
    # 找出最高票选项
    max_option = max(counts, key=counts.get)
    max_votes = counts[max_option]
    min_option = min(counts, key=counts.get)
    min_votes = counts[min_option]
    
    # 构建选项详情字符串
    options_detail = "、".join([f"{opt}{counts[opt]}票" for opt in counts])
    
    # 计算百分比
    if total_votes > 0:
        max_percent = round(max_votes / total_votes * 100, 1)
    else:
        max_percent = 0
    
    # 系统提示词
    system_prompt = """你是一位亲切的小学数学老师，正在给三年级学生讲解数据的收集与整理。
请用活泼、鼓励的语气，针对以下班级投票结果进行解读。
要求：
1. 先说最受欢迎的结果和票数
2. 再说最少被选的结果和票数
3. 用简单的话解释这个结果意味着什么
4. 最后给出一条基于数据的教学或活动建议
5. 总字数控制在150字以内
6. 适当使用emoji，但不要过于频繁"""
    
    # 用户提示词
    user_prompt = f"""投票主题：{topic}
各选项票数：{dict(counts)}
总投票人数：{total_votes}人
最受欢迎选项：{max_option}（{max_votes}票，占{max_percent}%）
请进行解读："""
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
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
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"⚠️ API调用失败：{response.status_code}"
    except requests.exceptions.Timeout:
        return "⏰ 请求超时，请检查网络连接"
    except Exception as e:
        return f"❌ 发生错误：{str(e)}"


# ========== 辅助函数：本地规则分析（备用） ==========
def local_analysis(topic, counts, total_votes):
    """当没有配置API Key或API失败时，使用本地规则生成分析"""
    if total_votes == 0:
        return "还没有投票数据，请等待同学参与~"
    
    max_option = max(counts, key=counts.get)
    max_votes = counts[max_option]
    max_percent = round(max_votes / total_votes * 100, 1)
    
    min_option = min(counts, key=counts.get)
    min_votes = counts[min_option]
    
    analysis = f"📊 根据投票结果：\n\n"
    analysis += f"🥇 最受欢迎的是「{max_option}」，获得 {max_votes} 票，占 {max_percent}%。\n"
    analysis += f"🥉 得票最少的是「{min_option}」，获得 {min_votes} 票。\n\n"
    
    if max_percent > 50:
        analysis += f"✨ 超过半数的同学选择了「{max_option}」，说明大家都很喜欢这个！"
    else:
        analysis += f"💡 各选项之间的差距不大，说明同学们有不同偏好，都很正常哦！"
    
    analysis += f"\n\n💪 建议：可以请选择「{min_option}」的同学分享一下想法，听听不同的声音。"
    
    return analysis


# ========== 侧边栏提示 ==========
with st.sidebar:
    st.header("⚙️ 系统状态")
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "YOUR_API_KEY_HERE":
        st.success("✅ AI大模型已就绪（DeepSeek）")
        st.caption(f"API Key: {DEEPSEEK_API_KEY[:10]}...")
    else:
        st.warning("⚠️ 未配置API Key，将使用本地规则分析")
        st.caption("如需AI智能解读，请在代码第14行填入DeepSeek API Key")
    st.markdown("---")

# ========== 主标题 ==========
st.title("📊 班级投票实时统计看板")
st.markdown("**小学数学数据收集与整理专用**")

# ========== 教师控制台 ==========
with st.sidebar:
    st.markdown("---")
    st.header("👩‍🏫 教师控制台")
    
    topic = st.text_input("📝 投票主题", "最喜欢的运动")
    options_text = st.text_area(
        "📋 选项（每行一个）",
        "篮球\n足球\n乒乓球\n跳绳\n羽毛球",
        help="每个选项单独一行"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 生成新投票", use_container_width=True):
            option_list = [opt.strip() for opt in options_text.split("\n") if opt.strip()]
            if len(option_list) < 2:
                st.error("至少需要2个选项")
            else:
                vote_code = str(random.randint(100000, 999999))
                st.session_state.votes[vote_code] = {
                    "topic": topic,
                    "options": option_list,
                    "counts": {opt: 0 for opt in option_list},
                    "total_votes": 0
                }
                st.session_state.vote_records[vote_code] = set()
                st.success(f"✅ 投票已创建！\n\n**投票码：{vote_code}**")
    
    with col2:
        if st.button("🗑️ 清除所有投票", use_container_width=True):
            st.session_state.votes = {}
            st.session_state.vote_records = {}
            st.success("已清除所有投票数据")
            st.rerun()

# ========== 学生投票区 ==========
st.subheader("🎯 学生投票区")
vote_code_input = st.text_input("请输入6位投票码", placeholder="例如：3827")

if vote_code_input and vote_code_input in st.session_state.votes:
    vdata = st.session_state.votes[vote_code_input]
    
    st.markdown(f"### 📌 {vdata['topic']}")
    
    voter_key = f"voted_{vote_code_input}"
    if voter_key not in st.session_state:
        st.session_state[voter_key] = False
    
    if st.session_state[voter_key]:
        st.warning("✅ 您已经投过票了！")
    else:
        choice = st.radio(
            "请选择一项：",
            vdata["options"],
            index=None,
            horizontal=True
        )
        
        if st.button("📮 提交投票", type="primary", use_container_width=True):
            if choice:
                vdata["counts"][choice] += 1
                vdata["total_votes"] += 1
                st.session_state[voter_key] = True
                st.success("🎉 投票成功！")
                st.balloons()
                st.rerun()
            else:
                st.error("请先选择一个选项")
    
    # ========== 结果展示区 ==========
    st.markdown("---")
    st.subheader("📈 实时统计结果")
    
    df = pd.DataFrame({
        "选项": list(vdata["counts"].keys()),
        "票数": list(vdata["counts"].values())
    })
    df = df.sort_values("票数", ascending=False)
    
    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(
            df, 
            x="选项", 
            y="票数", 
            title=f"条形图 - {vdata['topic']}",
            text="票数",
            color="票数",
            color_continuous_scale="Blues"
        )
        fig_bar.update_traces(textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        fig_pie = px.pie(
            df, 
            names="选项", 
            values="票数", 
            title=f"饼图 - {vdata['topic']}",
            hole=0.4
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("📊 总投票人数", vdata["total_votes"])
    
    # ========== AI智能解读区 ==========
    st.markdown("---")
    st.subheader("🤖 AI智能解读")
    
    if vdata["total_votes"] == 0:
        st.info("💡 还没有人投票，AI解读将在有数据后显示")
    else:
        if st.button("🔍 生成AI解读", type="secondary", use_container_width=True):
            with st.spinner("🤖 AI正在分析投票结果..."):
                # 尝试调用DeepSeek API
                analysis = call_deepseek_analysis(
                    vdata["topic"],
                    vdata["counts"],
                    vdata["total_votes"]
                )
                
                # 如果API返回None或失败，使用本地分析
                if analysis is None:
                    analysis = local_analysis(
                        vdata["topic"],
                        vdata["counts"],
                        vdata["total_votes"]
                    )
                    analysis += "\n\n---\n💡 *提示：配置API Key可获得更智能的解读*"
                
                st.session_state[f"analysis_{vote_code_input}"] = analysis
        
        if f"analysis_{vote_code_input}" in st.session_state:
            st.success(st.session_state[f"analysis_{vote_code_input}"])

elif vote_code_input:
    st.error("❌ 投票码不存在")
else:
    st.info("💡 请输入教师给出的6位投票码开始投票")

# ========== 教师工具 ==========
with st.expander("📋 教师工具：查看所有投票记录"):
    if st.session_state.votes:
        for code, info in st.session_state.votes.items():
            st.write(f"**{code}** - {info['topic']} | 共{info['total_votes']}人参与")
            for opt, cnt in info['counts'].items():
                st.write(f"  - {opt}: {cnt}票")
            st.markdown("---")
    else:
        st.write("暂无投票记录")

# ========== 页脚 ==========
st.markdown("---")
st.caption("🎓 小学数学教学专用工具 | 数据收集与整理单元")
