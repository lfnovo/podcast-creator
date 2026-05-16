"""
Podcast Creator Studio - Streamlit Interface

A comprehensive web interface for managing speaker profiles, episode profiles,
and generating podcasts using the podcast-creator library.
"""

import nest_asyncio
nest_asyncio.apply()

import os
import streamlit as st  # noqa: E402
import sys  # noqa: E402
import json  # noqa: E402
from copy import deepcopy  # noqa: E402
from pathlib import Path  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

# ``streamlit run`` 会把本文件所在目录加入 path，因而能 ``import utils``。
# ``podcast_creator`` 包在再往上两级目录的父级（仓库的 ``src/``）；仅追加 ``resources`` 无法 import。
_app_file = Path(__file__).resolve()
_podcast_pkg_parent = _app_file.parents[3]  # .../src 当路径为 src/podcast_creator/resources/streamlit_app/app.py
if str(_podcast_pkg_parent) not in sys.path:
    sys.path.insert(0, str(_podcast_pkg_parent))

# Import utilities
from utils import EpisodeManager, ProfileManager, ContentExtractor, run_async_in_streamlit, ErrorHandler, VoiceProvider, ProviderChecker  # noqa: E402

_STUDIO_BGM_OPTIONS = ("关闭", "片头 BGM（新闻播报风）", "全程 BGM")
_STUDIO_BGM_MODE_BY_LABEL = {
    "关闭": None,
    "片头 BGM（新闻播报风）": "intro",
    "全程 BGM": "full",
}


def _resolve_profile_working_dir() -> Path:
    """
    使用同时包含 speakers_config.json 与 episodes_config.json 的目录作为配置根目录。

    从当前工作目录向上查找最多 3 层，避免在子目录启动 Streamlit 时只读到不完整/占位配置。
    """
    start = Path.cwd()
    if (
        (start / "speakers_config.json").is_file()
        and (start / "episodes_config.json").is_file()
    ):
        return start.resolve()
    for ancestor in (start.parent, start.parent.parent, start.parent.parent.parent):
        if (
            (ancestor / "speakers_config.json").is_file()
            and (ancestor / "episodes_config.json").is_file()
        ):
            return ancestor.resolve()
    return start.resolve()


def _recover_from_legacy_clone_from_session_if_needed() -> None:
    """
    浏览器若仍保留已废弃的 ``clone_from_*`` Streamlit widget 键，单键 ``del`` 往往无法解除
    绑定，仍会报 ``cannot be modified after the widget is instantiated``。
    检测到这些键时：清空 session（仅保留导航相关字段）并立即 rerun 一次。
    """
    try:
        keys = list(st.session_state.keys())
    except Exception:
        return
    if not any(isinstance(k, str) and k.startswith("clone_from_") for k in keys):
        return

    page = st.session_state.get("current_page", "home")
    nav_lib = st.session_state.get("navigate_to_library", False)
    st.session_state.clear()
    st.session_state["current_page"] = page
    if nav_lib:
        st.session_state["navigate_to_library"] = nav_lib
    st.rerun()


# 配置文件、输出目录以此为准（可与终端 cwd 不同）
WORKING_DIR = _resolve_profile_working_dir()

# Auto-load environment variables from project .env so provider detection works in UI.
load_dotenv(WORKING_DIR / ".env", override=False)
load_dotenv(Path.cwd() / ".env", override=False)

# Normalize Ollama base URL for Esperanto/langchain-ollama compatibility.
# If users set /v1 for OpenAI-style endpoints, strip it for Ollama native client.
ollama_api_base = os.environ.get("OLLAMA_API_BASE", "").strip()
if ollama_api_base.endswith("/v1"):
    os.environ["OLLAMA_API_BASE"] = ollama_api_base[:-3].rstrip("/")

# Configure page
st.set_page_config(
    page_title="播客创作工作台",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 必须在任何其它 streamlit 元素之前处理遗留的 clone_from_* widget 会话（见函数说明）
_recover_from_legacy_clone_from_session_if_needed()

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f1f1f;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        margin: 0;
        opacity: 0.9;
    }
    
    .quick-action-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin: 0.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .quick-action-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)


def _apply_speaker_json_rules(json_text: str, focus_points: str = ""):
    """Apply common normalization rules for speaker profile JSON."""
    data = json.loads(json_text)
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("JSON 格式不正确：必须包含对象类型的 `profiles` 字段。")

    applied = []
    focus_lower = focus_points.lower()

    # Rule 1: unify provider from focus text keywords.
    target_provider = None
    for provider in [
        "piper",
        "gpt_sovits",
        "voicebox",
        "coqui",
        "edge_tts",
        "openai",
        "elevenlabs",
        "google",
    ]:
        if provider in focus_lower:
            target_provider = provider
            break
    if target_provider:
        for profile in profiles.values():
            if isinstance(profile, dict):
                profile["tts_provider"] = target_provider
        applied.append(f"统一 tts_provider 为 `{target_provider}`")

    # Rule 2: fill missing speaker fields.
    for profile in profiles.values():
        if not isinstance(profile, dict):
            continue
        speakers = profile.get("speakers", [])
        if isinstance(speakers, list):
            for idx, speaker in enumerate(speakers):
                if not isinstance(speaker, dict):
                    continue
                speaker.setdefault("name", f"Speaker {idx + 1}")
                speaker.setdefault("voice_id", "")
                speaker.setdefault("backstory", "")
                speaker.setdefault("personality", "")
    applied.append("补全 speaker 缺失字段（name/voice_id/backstory/personality）")

    return json.dumps(data, ensure_ascii=False, indent=2), applied


def _apply_episode_json_rules(json_text: str):
    """Apply common normalization rules for episode profile JSON."""
    data = json.loads(json_text)
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("JSON 格式不正确：必须包含对象类型的 `profiles` 字段。")

    applied = []
    for profile in profiles.values():
        if not isinstance(profile, dict):
            continue
        profile.setdefault("speaker_config", "")
        profile.setdefault("outline_provider", "ollama")
        profile.setdefault("transcript_provider", "ollama")
        profile.setdefault("outline_model", "qwen3:8b")
        profile.setdefault("transcript_model", "qwen3:8b")
        profile.setdefault("default_briefing", "")
        try:
            n = int(profile.get("num_segments", 3))
        except (TypeError, ValueError):
            n = 3
        profile["num_segments"] = max(1, min(10, n))
    applied.append("补全常用字段并规范 num_segments 到 1-10")

    return json.dumps(data, ensure_ascii=False, indent=2), applied


def _set_current_page(page: str):
    """Set route state."""
    st.session_state.current_page = page


def _render_deck_export_panel() -> None:
    """Render MVP Deck export panel in Streamlit."""
    st.subheader("🖼️ Export Deck（MVP）")
    st.caption("上传符合 Schema v1.0 的 JSON，一键导出单文件 HTML 幻灯。")

    try:
        from podcast_deck.exporter import DeckBuildOptions, export_deck
    except Exception as exc:  # pragma: no cover - UI defensive fallback
        st.warning(f"Deck 导出模块不可用：{exc}")
        return

    uploaded = st.file_uploader(
        "上传 deck/outline JSON",
        type=["json"],
        key="deck_export_file",
        help="需包含 schemaVersion/meta/slides。",
    )
    col1, col2 = st.columns(2)
    with col1:
        debug_script = st.checkbox(
            "包含调试脚本（仅本地调试）", value=False, key="deck_export_debug"
        )
    with col2:
        aspect_ratio = st.selectbox(
            "画面比例",
            options=["16:9", "4:3"],
            index=0,
            key="deck_export_ratio",
        )

    if uploaded is None:
        return

    if st.button("⚡ 生成 Deck HTML", type="primary", key="deck_export_run"):
        try:
            payload = json.loads(uploaded.getvalue().decode("utf-8"))
            deck_dir = WORKING_DIR / "output" / "decks"
            deck_dir.mkdir(parents=True, exist_ok=True)
            stem = Path(uploaded.name).stem or "deck"
            input_path = deck_dir / f"{stem}.json"
            output_path = deck_dir / f"{stem}.html"
            input_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            export_deck(
                input_path=input_path,
                output_path=output_path,
                options=DeckBuildOptions(
                    debug_script_enabled=debug_script, aspect_ratio=aspect_ratio
                ),
            )
            html_content = output_path.read_text(encoding="utf-8")
            st.success(f"✅ 导出成功：{output_path}")
            st.download_button(
                label="⬇️ 下载 deck.html",
                data=html_content,
                file_name=output_path.name,
                mime="text/html",
                key="deck_export_download",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"❌ Deck 导出失败：{exc}")


def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<div class="main-header">🎙️ Podcast Creator Studio</div>', unsafe_allow_html=True)
    
    page_labels = {
        "home": "🏠 首页",
        "speaker_profiles": "🎙️ 说话人配置",
        "episode_profiles": "📺 剧集配置",
        "generate_podcast": "🎬 生成播客",
        "episode_library": "📚 剧集库",
    }

    # Initialize current page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "home"
    
    # Handle programmatic navigation
    if st.session_state.get('navigate_to_library', False):
        _set_current_page("episode_library")
        st.session_state.navigate_to_library = False
    
    # Sidebar navigation
    with st.sidebar:
        st.title("导航")
        st.markdown("---")
        
        # Navigation menu
        pages = list(page_labels.keys())
        
        # Find current page index
        current_index = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0
        
        page = st.selectbox(
            "选择页面：",
            pages,
            index=current_index,
            format_func=lambda x: page_labels[x]
        )
        
        # Update current page if changed
        if page != st.session_state.current_page:
            _set_current_page(page)
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 快捷操作")
        
        if st.button("🎬 生成播客", use_container_width=True, key="sidebar_generate_podcast"):
            _set_current_page("generate_podcast")
            st.rerun()
            
        if st.button("📚 查看剧集", use_container_width=True, key="sidebar_view_episodes"):
            _set_current_page("episode_library")
            st.rerun()
    
    # Use the current page from session state
    page = st.session_state.current_page
    
    # Route to appropriate page
    if page == "home":
        show_home_page()
    elif page == "speaker_profiles":
        show_speaker_profiles_page()
    elif page == "episode_profiles":
        show_episode_profiles_page()
    elif page == "generate_podcast":
        show_generate_podcast_page()
    elif page == "episode_library":
        show_episode_library_page()

def show_home_page():
    """Display the home page with dashboard and quick stats."""
    st.subheader("欢迎使用播客创作工作台")
    st.markdown("你的 AI 播客一站式工作台")
    
    # Initialize managers
    episode_manager = EpisodeManager(base_output_dir=WORKING_DIR / "output")
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    
    # Get stats
    try:
        episodes_stats = episode_manager.get_episodes_stats()
        profiles_stats = profile_manager.get_profiles_stats()
        
        # Quick stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{episodes_stats['total_episodes']}</p>
                <p class="stat-label">剧集总数</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{profiles_stats['speaker_profiles_count']}</p>
                <p class="stat-label">说话人配置</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{profiles_stats['episode_profiles_count']}</p>
                <p class="stat-label">剧集配置</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Recent episodes
        st.subheader("最近剧集")
        
        recent_episodes = episode_manager.scan_episodes_directory()
        if recent_episodes:
            for episode in recent_episodes[:5]:  # Show last 5 episodes
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{episode.name}**")
                    if episode.created_date:
                        st.markdown(f"*创建时间：{episode.created_date.strftime('%Y-%m-%d %H:%M')}*")
                    if episode.duration:
                        st.markdown(f"*时长：{episode_manager.format_duration(episode.duration)}*")
                
                with col2:
                    if episode.audio_file and st.button("▶️ 播放", key=f"play_{episode.name}"):
                        st.session_state.selected_episode = episode
                        _set_current_page("episode_library")
                        st.rerun()
                
                with col3:
                    if st.button("📄 详情", key=f"details_{episode.name}"):
                        st.session_state.selected_episode = episode
                        _set_current_page("episode_library")
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("📝 暂无剧集，先生成你的第一期播客吧！")
        
        st.markdown("---")
        
        # Provider Status
        st.markdown("---")
        ProviderChecker.show_provider_status()
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("快捷操作")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎬 新建播客", use_container_width=True, type="primary"):
                _set_current_page("generate_podcast")
                st.rerun()
        
        with col2:
            if st.button("📁 导入配置", use_container_width=True):
                _set_current_page("speaker_profiles")
                st.rerun()

        st.markdown("---")
        _render_deck_export_panel()
    
    except Exception as e:
        st.error(f"首页数据加载失败：{str(e)}")
        st.markdown("请确认必需文件已就绪后重试。")

def show_speaker_profiles_page():
    """Display the speaker profiles management page."""
    st.subheader("🎙️ 说话人配置")
    st.markdown("管理你的说话人配置")
    
    # Initialize profile manager
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    
    # Load profiles
    try:
        profiles = profile_manager.load_speaker_profiles()
        profile_names = list(profiles.get("profiles", {}).keys())
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ 新建配置", use_container_width=True):
                st.session_state.show_new_speaker_form = True
                st.rerun()
        
        with col2:
            if st.button("📁 导入", use_container_width=True):
                st.session_state.show_import_speaker_form = True
                st.rerun()
        
        with col3:
            if st.button("💾 导出全部", use_container_width=True):
                export_data = profile_manager.export_speaker_profiles()
                st.download_button(
                    label="下载 speakers_config.json",
                    data=json.dumps(export_data, indent=2),
                    file_name="speakers_config.json",
                    mime="application/json"
                )
        
        st.markdown("---")
        
        # Import form
        if st.session_state.get("show_import_speaker_form", False):
            st.subheader("📁 导入说话人配置")
            speaker_import_key_prefix = "speaker_import"
            
            uploaded_file = st.file_uploader(
                "选择要导入的文件（支持 .json / .docx）",
                type=['json', 'docx'],
                key=f"{speaker_import_key_prefix}_file"
            )
            
            if uploaded_file is not None:
                try:
                    parsed_json_text = profile_manager.parse_import_file(
                        uploaded_file.name, uploaded_file.read(), profile_kind="speaker"
                    )
                    st.markdown("### 预处理与确认")
                    st.info("已预处理为 JSON。请先补充关注点并按需编辑，再确认生成 JSON。")

                    speaker_focus_points = st.text_area(
                        "请补充本次关注点（可选）",
                        key=f"{speaker_import_key_prefix}_focus_points",
                        placeholder="例如：统一 tts_provider 为 piper；检查每个 speaker 的 voice_id 是否为空；保持 profile 命名规范。",
                        help="用于人工检查导入内容，当前不会自动改写 JSON。"
                    )
                    if speaker_focus_points.strip():
                        st.caption(f"已记录关注点：{speaker_focus_points.strip()}")

                    edited_json = st.text_area(
                        "编辑预处理后的 JSON",
                        value=parsed_json_text,
                        height=320,
                        key=f"{speaker_import_key_prefix}_edited_json"
                    )

                    if st.button("✨ 根据关注点自动应用规则", key=f"{speaker_import_key_prefix}_apply_rules_btn"):
                        updated_json, applied_rules = _apply_speaker_json_rules(
                            edited_json, speaker_focus_points
                        )
                        st.session_state[f"{speaker_import_key_prefix}_edited_json"] = updated_json
                        st.success("已应用规则：" + "；".join(applied_rules))
                        st.rerun()

                    generated_speaker_json = None
                    if st.button("🧪 确认并生成 JSON", key=f"{speaker_import_key_prefix}_generate_json_btn"):
                        candidate = json.loads(edited_json)
                        if "profiles" not in candidate or not isinstance(candidate["profiles"], dict):
                            st.error("❌ JSON 格式不正确：必须包含对象类型的 `profiles` 字段。")
                        else:
                            generated_speaker_json = json.dumps(candidate, ensure_ascii=False, indent=2)
                            st.success("✅ JSON 校验通过，已生成可下载文件。")
                            st.download_button(
                                label="⬇️ 下载生成后的 speakers_config.import.json",
                                data=generated_speaker_json,
                                file_name="speakers_config.import.json",
                                mime="application/json",
                                key=f"{speaker_import_key_prefix}_download_generated_json"
                            )
                            if st.button("🚀 导入该 JSON", key=f"{speaker_import_key_prefix}_import_generated_json"):
                                imported_names = profile_manager.import_speaker_profiles(generated_speaker_json)
                                if imported_names:
                                    st.success(f"✅ 成功导入 {len(imported_names)} 个配置：{', '.join(imported_names)}")
                                    st.session_state.show_import_speaker_form = False
                                    st.rerun()
                                else:
                                    st.warning("⚠️ 没有导入新配置，请检查是否重名或文件格式是否正确。")
                except Exception as e:
                    st.error(f"❌ 导入配置失败：{str(e)}")
            
            if st.button("❌ 取消导入", key=f"{speaker_import_key_prefix}_cancel_import"):
                st.session_state.show_import_speaker_form = False
                st.rerun()
            
            st.markdown("---")
        
        # New profile form
        if st.session_state.get("show_new_speaker_form", False):
            st.subheader("➕ 新建说话人配置")
            
            profile_name = st.text_input("配置名称：", placeholder="例如：my_podcasters", key="new_profile_name")
            
            col1, col2 = st.columns(2)
            with col1:
                tts_provider = ProviderChecker.render_tts_provider_selector(
                    "TTS 提供商：",
                    current_provider="elevenlabs",
                    key="new_tts_provider",
                    help_text="选择一个文本转语音（TTS）提供商"
                )
            with col2:
                # Get default model for selected provider
                defaults = ProviderChecker.get_default_models(tts_provider)
                default_model = defaults.get("tts", "eleven_flash_v2_5")
                tts_model = st.text_input("TTS 模型：", value=default_model, key="new_tts_model")
            
            new_edge_tts_config = None
            if tts_provider == "edge_tts":
                st.markdown("### Edge TTS 全局韵律")
                st.caption(
                    "与 `speakers_config` 中一致：**语速 / 音高 / 音量** 对同一条配置里的所有角色生效。"
                    " 下方为系统推荐预设，可一键应用后再微调。"
                )
                new_edge_tts_config = VoiceProvider.render_edge_tts_prosody_ui("new_speaker_prof", None)

            new_gpt_tts_config = None
            if tts_provider == "gpt_sovits":
                new_gpt_tts_config = VoiceProvider.render_gpt_sovits_config_ui(
                    "new_speaker_prof", None
                )

            new_voicebox_tts_config = None
            if tts_provider == "voicebox":
                new_voicebox_tts_config = VoiceProvider.render_voicebox_config_ui(
                    "new_speaker_prof", None
                )
            
            st.markdown("### 说话人")
            st.caption(
                "多人播客：1–4 位说话人；**姓名**、**voice_id** 各自不能重复，且对白里的 `speaker` "
                "必须与姓名完全一致。中文双人：`zh_duo_local` / `zh_duo_talk_edge`，新闻感双人：`zh_duo_news_local` / `zh_duo_news_edge`。"
            )
            
            # Initialize speakers in session state
            if 'new_speakers' not in st.session_state:
                st.session_state.new_speakers = [{'name': '', 'voice_id': '', 'backstory': '', 'personality': ''}]
            
            for i, speaker in enumerate(st.session_state.new_speakers):
                st.markdown(f"**说话人 {i+1}：**")
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    speaker_name = st.text_input("姓名：", key=f"new_speaker_name_{i}", value=speaker.get('name', ''))
                    
                    if tts_provider == "gpt_sovits":
                        VoiceProvider.render_gpt_sovits_speaker_file_upload(
                            working_dir=WORKING_DIR,
                            key_prefix="new_speaker_prof",
                            speaker_index=i,
                            voice_id_state_key=f"new_voice_id_{i}",
                        )
                    
                    # Voice selection with provider-specific voices
                    voice_id = VoiceProvider.render_voice_selector(
                        provider=tts_provider,
                        model=tts_model,
                        current_voice_id=speaker.get('voice_id', ''),
                        key=f"new_voice_id_{i}",
                        help_text=f"从 {tts_provider} 中选择音色"
                    )
                    
                    VoiceProvider.render_speaker_voice_audition(
                        tts_provider,
                        voice_id,
                        edge_prosody=new_edge_tts_config,
                        key_prefix=f"new_spk_{i}",
                    )
                    
                    backstory = st.text_area("背景设定：", key=f"new_backstory_{i}", value=speaker.get('backstory', ''))
                    personality = st.text_area("性格特点：", key=f"new_personality_{i}", value=speaker.get('personality', ''))
                    
                    # Update speaker data
                    st.session_state.new_speakers[i] = {
                        'name': speaker_name,
                        'voice_id': voice_id,
                        'backstory': backstory,
                        'personality': personality
                    }
                
                with col2:
                    if len(st.session_state.new_speakers) > 1:
                        if st.button("🗑️", key=f"new_remove_speaker_{i}"):
                            st.session_state.new_speakers.pop(i)
                            st.rerun()
                
                st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ 添加说话人", key="new_add_speaker") and len(st.session_state.new_speakers) < 4:
                    st.session_state.new_speakers.append({'name': '', 'voice_id': '', 'backstory': '', 'personality': ''})
                    st.rerun()
            
            st.markdown("---")
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ 创建配置", type="primary", key="create_speaker_profile"):
                    if not profile_name:
                        st.error("请填写配置名称")
                    elif profile_name in profile_names:
                        st.error(f"配置 '{profile_name}' 已存在")
                    else:
                        # Create profile data
                        profile_data = {
                            "tts_provider": tts_provider,
                            "tts_model": tts_model,
                            "speakers": st.session_state.new_speakers
                        }
                        if tts_provider == "edge_tts" and new_edge_tts_config:
                            profile_data["tts_config"] = dict(new_edge_tts_config)
                        elif tts_provider == "gpt_sovits" and new_gpt_tts_config is not None:
                            profile_data["tts_config"] = dict(new_gpt_tts_config)
                        elif tts_provider == "voicebox" and new_voicebox_tts_config is not None:
                            profile_data["tts_config"] = dict(new_voicebox_tts_config)
                        
                        # Validate profile
                        validation_errors = profile_manager.validate_speaker_profile(profile_data)
                        if validation_errors:
                            st.error("❌ 校验失败：")
                            for error in validation_errors:
                                st.error(f"• {error}")
                        else:
                            # Create the profile
                            if profile_manager.create_speaker_profile(profile_name, profile_data):
                                st.success(f"✅ 配置 '{profile_name}' 创建成功！")
                                st.session_state.show_new_speaker_form = False
                                if 'new_speakers' in st.session_state:
                                    del st.session_state.new_speakers
                                st.rerun()
                            else:
                                st.error("❌ 创建配置失败")
            
            with col2:
                if st.button("❌ 取消", key="cancel_new_speaker"):
                    st.session_state.show_new_speaker_form = False
                    if 'new_speakers' in st.session_state:
                        del st.session_state.new_speakers
                    st.rerun()
            
            st.markdown("---")
        
        # Edit profile form
        if st.session_state.get("edit_speaker_profile"):
            edit_profile_name = st.session_state.edit_speaker_profile
            edit_profile_data = profile_manager.get_speaker_profile(edit_profile_name)
            
            if edit_profile_data:
                st.subheader(f"✏️ 编辑说话人配置：{edit_profile_name}")
                
                col1, col2 = st.columns(2)
                with col1:
                    current_tts_provider = edit_profile_data.get('tts_provider', 'elevenlabs')
                    tts_provider = ProviderChecker.render_tts_provider_selector(
                        "TTS 提供商：",
                        current_provider=current_tts_provider,
                        key="edit_speaker_tts_provider",
                        help_text="选择一个文本转语音（TTS）提供商"
                    )
                with col2:
                    # Get default model for selected provider
                    defaults = ProviderChecker.get_default_models(tts_provider)
                    default_model = defaults.get("tts", "eleven_flash_v2_5")
                    
                    current_tts_model = edit_profile_data.get('tts_model', default_model)
                    tts_model = st.text_input(
                        "TTS 模型：", 
                        value=current_tts_model,
                        key="edit_speaker_tts_model"
                    )
                
                edit_edge_tts_config = None
                if tts_provider == "edge_tts":
                    st.markdown("### Edge TTS 全局韵律")
                    st.caption(
                        "调节后保存将写入当前配置的 `tts_config`。可选用系统推荐预设后再微调。"
                    )
                    edit_edge_tts_config = VoiceProvider.render_edge_tts_prosody_ui(
                        f"edit_speaker_{edit_profile_name}",
                        edit_profile_data.get("tts_config"),
                    )

                edit_gpt_tts_config = None
                if tts_provider == "gpt_sovits":
                    edit_gpt_tts_config = VoiceProvider.render_gpt_sovits_config_ui(
                        f"edit_gpt_{edit_profile_name}",
                        edit_profile_data.get("tts_config"),
                    )

                edit_voicebox_tts_config = None
                if tts_provider == "voicebox":
                    edit_voicebox_tts_config = VoiceProvider.render_voicebox_config_ui(
                        f"edit_vb_{edit_profile_name}",
                        edit_profile_data.get("tts_config"),
                    )
                
                st.markdown("### 说话人")
                
                # Initialize edit speakers
                if 'edit_speakers' not in st.session_state:
                    st.session_state.edit_speakers = edit_profile_data.get('speakers', [])
                
                for i, speaker in enumerate(st.session_state.edit_speakers):
                    st.markdown(f"**说话人 {i+1}：**")
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        speaker_name = st.text_input(
                            "姓名：", 
                            key=f"edit_speaker_name_{i}", 
                            value=speaker.get('name', '')
                        )
                        
                        if tts_provider == "gpt_sovits":
                            VoiceProvider.render_gpt_sovits_speaker_file_upload(
                                working_dir=WORKING_DIR,
                                key_prefix=f"edit_gpt_{edit_profile_name}",
                                speaker_index=i,
                                voice_id_state_key=f"edit_voice_id_{i}",
                            )
                        
                        # Voice selection with provider-specific voices
                        voice_id = VoiceProvider.render_voice_selector(
                            provider=tts_provider,
                            model=tts_model,
                            current_voice_id=speaker.get('voice_id', ''),
                            key=f"edit_voice_id_{i}",
                            help_text=f"从 {tts_provider} 中选择音色"
                        )
                        
                        VoiceProvider.render_speaker_voice_audition(
                            tts_provider,
                            voice_id,
                            edge_prosody=edit_edge_tts_config,
                            key_prefix=f"edit_spk_{edit_profile_name}_{i}",
                        )
                        
                        backstory = st.text_area(
                            "背景设定：", 
                            key=f"edit_backstory_{i}", 
                            value=speaker.get('backstory', '')
                        )
                        personality = st.text_area(
                            "性格特点：", 
                            key=f"edit_personality_{i}", 
                            value=speaker.get('personality', '')
                        )
                        
                        # Update speaker data
                        st.session_state.edit_speakers[i] = {
                            'name': speaker_name,
                            'voice_id': voice_id,
                            'backstory': backstory,
                            'personality': personality
                        }
                    
                    with col2:
                        if len(st.session_state.edit_speakers) > 1:
                            if st.button("🗑️", key=f"edit_remove_speaker_{i}"):
                                st.session_state.edit_speakers.pop(i)
                                st.rerun()
                    
                    st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("➕ 添加说话人", key="edit_add_speaker") and len(st.session_state.edit_speakers) < 4:
                        st.session_state.edit_speakers.append({'name': '', 'voice_id': '', 'backstory': '', 'personality': ''})
                        st.rerun()
                
                st.markdown("---")
                
                # Action buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ 保存修改", type="primary", key="save_speaker_changes"):
                        # Update profile data
                        updated_profile_data = {
                            "tts_provider": tts_provider,
                            "tts_model": tts_model,
                            "speakers": st.session_state.edit_speakers
                        }
                        tc = dict(edit_profile_data.get("tts_config") or {})
                        if tts_provider == "edge_tts" and edit_edge_tts_config:
                            tc.update(edit_edge_tts_config)
                            updated_profile_data["tts_config"] = tc
                        elif tts_provider == "gpt_sovits" and edit_gpt_tts_config is not None:
                            updated_profile_data["tts_config"] = dict(edit_gpt_tts_config)
                        elif tts_provider == "voicebox" and edit_voicebox_tts_config is not None:
                            updated_profile_data["tts_config"] = dict(edit_voicebox_tts_config)
                        elif tc:
                            updated_profile_data["tts_config"] = tc
                        
                        # Validate profile
                        validation_errors = profile_manager.validate_speaker_profile(updated_profile_data)
                        if validation_errors:
                            st.error("❌ 校验失败：")
                            for error in validation_errors:
                                st.error(f"• {error}")
                        else:
                            # Update the profile
                            if profile_manager.update_speaker_profile(edit_profile_name, updated_profile_data):
                                st.success(f"✅ 配置 '{edit_profile_name}' 更新成功！")
                                st.session_state.edit_speaker_profile = None
                                if 'edit_speakers' in st.session_state:
                                    del st.session_state.edit_speakers
                                st.rerun()
                            else:
                                st.error("❌ 更新配置失败")
                
                with col2:
                    if st.button("❌ 取消编辑", key="cancel_edit_speaker"):
                        st.session_state.edit_speaker_profile = None
                        if 'edit_speakers' in st.session_state:
                            del st.session_state.edit_speakers
                        st.rerun()
                
                st.markdown("---")
            else:
                st.error(f"未找到说话人配置 '{edit_profile_name}'")
                st.session_state.edit_speaker_profile = None
                st.rerun()
        
        # Display existing profiles
        st.subheader("已有说话人配置")
        
        if profile_names:
            for profile_name in profile_names:
                profile_data = profiles["profiles"][profile_name]
                
                with st.expander(f"🎙️ {profile_name}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**TTS 提供商：** {profile_data.get('tts_provider', 'N/A')}")
                        st.markdown(f"**TTS 模型：** {profile_data.get('tts_model', 'N/A')}")
                        st.markdown(f"**说话人数：** {len(profile_data.get('speakers', []))}")
                        
                        # Show speakers
                        speakers = profile_data.get('speakers', [])
                        if speakers:
                            st.markdown("**说话人：**")
                            prof_edge = (
                                profile_data.get("tts_config")
                                if profile_data.get("tts_provider") == "edge_tts"
                                else None
                            )
                            for i, speaker in enumerate(speakers):
                                st.markdown(
                                    f"• **{speaker.get('name', '未命名')}** — `{speaker.get('voice_id', '无 voice_id')}`"
                                )
                                VoiceProvider.render_speaker_voice_audition(
                                    profile_data.get("tts_provider", ""),
                                    speaker.get("voice_id", ""),
                                    edge_prosody=prof_edge,
                                    key_prefix=f"lib_{profile_name}_{i}",
                                )
                        
                        if profile_data.get("tts_provider") == "edge_tts":
                            with st.expander("🎛️ 调节韵律并另存为新配置（副本）", expanded=False):
                                st.caption(
                                    "不修改当前配置：根据下方韵律生成一条**新**说话人配置，便于对比试听。"
                                    " 名称请勿与现有配置重复。"
                                )
                                clone_name = st.text_input(
                                    "新配置名称",
                                    value=f"{profile_name}_tuned",
                                    key=f"edge_clone_name_{profile_name}",
                                )
                                clone_prosody = VoiceProvider.render_edge_tts_prosody_ui(
                                    f"edge_prosody_saveas_{profile_name}",
                                    profile_data.get("tts_config"),
                                )
                                if st.button("另存为新配置", key=f"edge_clone_save_{profile_name}"):
                                    name_ok = clone_name.strip()
                                    if not name_ok:
                                        st.error("请填写新配置名称")
                                    elif name_ok in profile_manager.get_speaker_profile_names():
                                        st.error("该名称已存在，请换一个。")
                                    else:
                                        new_prof = deepcopy(profile_data)
                                        tc = dict(new_prof.get("tts_config") or {})
                                        tc.update(clone_prosody)
                                        new_prof["tts_config"] = tc
                                        if profile_manager.create_speaker_profile(name_ok, new_prof):
                                            st.success(f"✅ 已保存副本「{name_ok}」")
                                            st.rerun()
                                        else:
                                            st.error("保存失败。")
                    
                    with col2:
                        st.markdown("**操作：**")
                        
                        # Edit button
                        if st.button("✏️ 编辑", key=f"edit_{profile_name}"):
                            st.session_state.edit_speaker_profile = profile_name
                            st.rerun()
                        
                        # Clone button
                        if st.button("📋 克隆", key=f"clone_{profile_name}"):
                            new_name = profile_manager.allocate_clone_name(profile_name, for_episode=False)
                            if profile_manager.clone_speaker_profile(profile_name, new_name):
                                st.success(f"✅ 配置已克隆为 '{new_name}'")
                                st.rerun()
                            else:
                                st.error("❌ 克隆配置失败")
                        
                        # Export button
                        export_data = profile_manager.export_speaker_profiles([profile_name])
                        st.download_button(
                            label="💾 导出",
                            data=json.dumps(export_data, indent=2),
                            file_name=f"{profile_name}_speaker_config.json",
                            mime="application/json",
                            key=f"export_{profile_name}"
                        )
                        
                        # Delete button
                        if st.button("🗑️ 删除", key=f"delete_{profile_name}"):
                            if profile_manager.delete_speaker_profile(profile_name):
                                st.success(f"✅ 配置 '{profile_name}' 已删除")
                                st.rerun()
                            else:
                                st.error("❌ 删除配置失败")
        else:
            st.info("还没有说话人配置，先创建一个吧。")
    
    except Exception as e:
        st.error(f"加载说话人配置失败：{str(e)}")
        st.markdown("请检查配置文件后重试。")

def show_episode_profiles_page():
    """Display the episode profiles management page."""
    st.subheader("📺 剧集配置")
    st.markdown("管理你的剧集配置")
    
    # Define available providers for use throughout the function
    all_providers = ["openai", "anthropic", "google", "groq", "ollama", "openrouter", "azure", "mistral", "deepseek", "xai"]
    
    # Initialize profile manager
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    
    # Load profiles
    try:
        profiles = profile_manager.load_episode_profiles()
        profile_names = list(profiles.get("profiles", {}).keys())
        speaker_profile_names = profile_manager.get_speaker_profile_names()
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ 新建配置", use_container_width=True):
                st.session_state.show_new_episode_form = True
                st.rerun()
        
        with col2:
            if st.button("📁 导入", use_container_width=True):
                st.session_state.show_import_episode_form = True
                st.rerun()
        
        with col3:
            if st.button("💾 导出全部", use_container_width=True):
                export_data = profile_manager.export_episode_profiles()
                st.download_button(
                    label="下载 episodes_config.json",
                    data=json.dumps(export_data, indent=2),
                    file_name="episodes_config.json",
                    mime="application/json"
                )
        
        st.markdown("---")
        
        # Import form
        if st.session_state.get("show_import_episode_form", False):
            st.subheader("📁 导入剧集配置")
            episode_import_key_prefix = "episode_import"
            
            uploaded_file = st.file_uploader(
                "选择要导入的文件（支持 .json / .docx）",
                type=['json', 'docx'],
                key=f"{episode_import_key_prefix}_file"
            )
            
            if uploaded_file is not None:
                try:
                    parsed_json_text = profile_manager.parse_import_file(
                        uploaded_file.name, uploaded_file.read(), profile_kind="episode"
                    )
                    st.markdown("### 预处理与确认")
                    st.info("已预处理为 JSON。请先补充关注点并按需编辑，再确认生成 JSON。")

                    episode_focus_points = st.text_area(
                        "请补充本次关注点（可选）",
                        key=f"{episode_import_key_prefix}_focus_points",
                        placeholder="例如：检查 speaker_config 是否存在；统一模型命名；num_segments 控制在 1-10。",
                        help="用于人工检查导入内容，当前不会自动改写 JSON。"
                    )
                    if episode_focus_points.strip():
                        st.caption(f"已记录关注点：{episode_focus_points.strip()}")

                    edited_json = st.text_area(
                        "编辑预处理后的 JSON",
                        value=parsed_json_text,
                        height=320,
                        key=f"{episode_import_key_prefix}_edited_json"
                    )

                    if st.button("✨ 自动规范字段与分段", key=f"{episode_import_key_prefix}_apply_rules_btn"):
                        updated_json, applied_rules = _apply_episode_json_rules(edited_json)
                        st.session_state[f"{episode_import_key_prefix}_edited_json"] = updated_json
                        st.success("已应用规则：" + "；".join(applied_rules))
                        st.rerun()

                    generated_episode_json = None
                    if st.button("🧪 确认并生成 JSON", key=f"{episode_import_key_prefix}_generate_json_btn"):
                        candidate = json.loads(edited_json)
                        if "profiles" not in candidate or not isinstance(candidate["profiles"], dict):
                            st.error("❌ JSON 格式不正确：必须包含对象类型的 `profiles` 字段。")
                        else:
                            generated_episode_json = json.dumps(candidate, ensure_ascii=False, indent=2)
                            st.success("✅ JSON 校验通过，已生成可下载文件。")
                            st.download_button(
                                label="⬇️ 下载生成后的 episodes_config.import.json",
                                data=generated_episode_json,
                                file_name="episodes_config.import.json",
                                mime="application/json",
                                key=f"{episode_import_key_prefix}_download_generated_json"
                            )
                            if st.button("🚀 导入该 JSON", key=f"{episode_import_key_prefix}_import_generated_json"):
                                imported_names = profile_manager.import_episode_profiles(generated_episode_json)
                                if imported_names:
                                    st.success(f"✅ 成功导入 {len(imported_names)} 个配置：{', '.join(imported_names)}")
                                    st.session_state.show_import_episode_form = False
                                    st.rerun()
                                else:
                                    st.warning("⚠️ 没有导入新配置，请检查是否重名或文件格式是否正确。")
                except Exception as e:
                    st.error(f"❌ 导入配置失败：{str(e)}")
            
            if st.button("❌ 取消导入", key=f"{episode_import_key_prefix}_cancel_import"):
                st.session_state.show_import_episode_form = False
                st.rerun()
            
            st.markdown("---")
        
        # New profile form
        if st.session_state.get("show_new_episode_form", False):
            st.subheader("➕ 新建剧集配置")
            
            profile_name = st.text_input("配置名称：", placeholder="例如：my_tech_talks", key="new_episode_name")
            
            if speaker_profile_names:
                speaker_config = st.selectbox("说话人配置：", speaker_profile_names, key="new_episode_speaker")
            else:
                st.error("⚠️ 未找到说话人配置，请先创建。")
                speaker_config = None
            
            st.markdown("### AI 模型配置")
            
            # Outline Model Configuration
            st.markdown("**大纲生成：**")
            col1, col2 = st.columns(2)
            with col1:
                outline_provider = ProviderChecker.render_provider_selector(
                    "大纲提供商：",
                    all_providers,
                    current_provider="ollama",
                    key="new_episode_outline_provider",
                    help_text="选择用于生成播客大纲的 AI 提供商"
                )
            with col2:
                # Get default model for selected provider
                defaults = ProviderChecker.get_default_models(outline_provider)
                default_outline_model = defaults.get("outline", "qwen3:8b")
                
                outline_model = st.text_input(
                    "大纲模型：",
                    value=default_outline_model,
                    placeholder=default_outline_model,
                    key="new_episode_outline_model"
                )
            
            # Transcript Model Configuration
            st.markdown("**对话稿生成：**")
            col1, col2 = st.columns(2)
            with col1:
                transcript_provider = ProviderChecker.render_provider_selector(
                    "对话稿提供商：",
                    all_providers,
                    current_provider="ollama",
                    key="new_episode_transcript_provider",
                    help_text="选择用于生成播客对话稿的 AI 提供商"
                )
            with col2:
                # Get default model for selected provider
                defaults = ProviderChecker.get_default_models(transcript_provider)
                default_transcript_model = defaults.get("transcript", "qwen3:8b")
                
                transcript_model = st.text_input(
                    "对话稿模型：",
                    value=default_transcript_model,
                    placeholder=default_transcript_model,
                    key="new_episode_transcript_model"
                )
            
            num_segments = st.slider("分段数量：", 1, 10, 4, key="new_episode_segments")

            language = st.text_input(
                "语言：",
                placeholder="例如：zh-CN、pt-BR、es（留空默认英文）",
                key="new_episode_language",
                help="播客生成语言代码，支持 ISO 639-1（如 `zh`）或 BCP 47（如 `zh-CN`）。"
            )

            default_briefing = st.text_area(
                "默认提示词：",
                value="请围绕主题生成结构清晰、表达自然的播客内容。",
                height=100,
                key="new_episode_briefing"
            )

            st.markdown("---")

            # Action buttons
            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ 创建配置", type="primary", key="create_episode_profile"):
                    if not profile_name:
                        st.error("请填写配置名称")
                    elif profile_name in profile_names:
                        st.error(f"配置 '{profile_name}' 已存在")
                    elif not speaker_config:
                        st.error("请选择说话人配置")
                    else:
                        # Create profile data with provider information
                        profile_data = {
                            "speaker_config": speaker_config,
                            "outline_model": outline_model,
                            "outline_provider": outline_provider,
                            "transcript_model": transcript_model,
                            "transcript_provider": transcript_provider,
                            "num_segments": num_segments,
                            "default_briefing": default_briefing
                        }
                        if language.strip():
                            profile_data["language"] = language.strip()
                        
                        # Validate profile
                        validation_errors = profile_manager.validate_episode_profile(profile_data)
                        if validation_errors:
                            st.error("❌ 校验失败：")
                            for error in validation_errors:
                                st.error(f"• {error}")
                        else:
                            # Create the profile
                            if profile_manager.create_episode_profile(profile_name, profile_data):
                                st.success(f"✅ 配置 '{profile_name}' 创建成功！")
                                st.session_state.show_new_episode_form = False
                                st.rerun()
                            else:
                                st.error("❌ 创建配置失败")
            
            with col2:
                if st.button("❌ 取消", key="cancel_new_episode"):
                    st.session_state.show_new_episode_form = False
                    st.rerun()
            
            st.markdown("---")
        
        # Edit profile form
        if st.session_state.get("edit_episode_profile"):
            edit_profile_name = st.session_state.edit_episode_profile
            edit_profile_data = profile_manager.get_episode_profile(edit_profile_name)
            
            if edit_profile_data:
                st.subheader(f"✏️ 编辑剧集配置：{edit_profile_name}")
                
                # Profile name (allow renaming)
                new_profile_name = st.text_input(
                    "配置名称：", 
                    value=edit_profile_name,
                    key="edit_episode_profile_name"
                )
                
                if speaker_profile_names:
                    current_speaker_index = 0
                    if edit_profile_data['speaker_config'] in speaker_profile_names:
                        current_speaker_index = speaker_profile_names.index(edit_profile_data['speaker_config'])
                    
                    speaker_config = st.selectbox(
                        "说话人配置：", 
                        speaker_profile_names, 
                        index=current_speaker_index,
                        key="edit_episode_speaker"
                    )
                else:
                    st.error("⚠️ 未找到说话人配置。")
                    speaker_config = edit_profile_data.get('speaker_config', '')
                
                st.markdown("### AI 模型配置")
                
                # Outline Model Configuration
                st.markdown("**大纲生成：**")
                col1, col2 = st.columns(2)
                with col1:
                    current_outline_provider = edit_profile_data.get('outline_provider', 'ollama')
                    outline_provider = ProviderChecker.render_provider_selector(
                        "大纲提供商：",
                        all_providers,
                        current_provider=current_outline_provider,
                        key="edit_episode_outline_provider",
                        help_text="选择用于生成播客大纲的 AI 提供商"
                    )
                with col2:
                    # Get default model for selected provider
                    defaults = ProviderChecker.get_default_models(outline_provider)
                    default_model = defaults.get("outline", "qwen3:8b")
                    
                    current_outline_model = edit_profile_data.get('outline_model', default_model)
                    outline_model = st.text_input(
                        "大纲模型：", 
                        value=current_outline_model,
                        placeholder=default_model,
                        key="edit_episode_outline_model"
                    )
                
                # Transcript Model Configuration
                st.markdown("**对话稿生成：**")
                col1, col2 = st.columns(2)
                with col1:
                    current_transcript_provider = edit_profile_data.get('transcript_provider', 'ollama')
                    transcript_provider = ProviderChecker.render_provider_selector(
                        "对话稿提供商：",
                        all_providers,
                        current_provider=current_transcript_provider,
                        key="edit_episode_transcript_provider",
                        help_text="选择用于生成播客对话稿的 AI 提供商"
                    )
                with col2:
                    # Get default model for selected provider
                    defaults = ProviderChecker.get_default_models(transcript_provider)
                    default_model = defaults.get("transcript", "qwen3:8b")
                    
                    current_transcript_model = edit_profile_data.get('transcript_model', default_model)
                    transcript_model = st.text_input(
                        "对话稿模型：", 
                        value=current_transcript_model,
                        placeholder=default_model,
                        key="edit_episode_transcript_model"
                    )
                
                num_segments = st.slider(
                    "分段数量：",
                    1, 10,
                    value=edit_profile_data.get('num_segments', 4),
                    key="edit_episode_segments"
                )

                language = st.text_input(
                    "语言：",
                    value=edit_profile_data.get('language', ''),
                    placeholder="例如：zh-CN、pt-BR、es（留空默认英文）",
                    key="edit_episode_language",
                    help="播客生成语言代码，支持 ISO 639-1（如 `zh`）或 BCP 47（如 `zh-CN`）。"
                )

                default_briefing = st.text_area(
                    "默认提示词：",
                    value=edit_profile_data.get('default_briefing', ''),
                    height=100,
                    key="edit_episode_briefing"
                )

                st.markdown("---")

                # Action buttons
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✅ 保存修改", type="primary", key="save_episode_changes"):
                        if not new_profile_name.strip():
                            st.error("配置名称不能为空")
                        elif new_profile_name != edit_profile_name and new_profile_name in profile_names:
                            st.error(f"配置名称 '{new_profile_name}' 已存在")
                        else:
                            # Update profile data with provider information
                            updated_profile_data = {
                                "speaker_config": speaker_config,
                                "outline_model": outline_model,
                                "outline_provider": outline_provider,
                                "transcript_model": transcript_model,
                                "transcript_provider": transcript_provider,
                                "num_segments": num_segments,
                                "default_briefing": default_briefing
                            }
                            if language.strip():
                                updated_profile_data["language"] = language.strip()
                            
                            # Validate profile
                            validation_errors = profile_manager.validate_episode_profile(updated_profile_data)
                            if validation_errors:
                                st.error("❌ 校验失败：")
                                for error in validation_errors:
                                    st.error(f"• {error}")
                            else:
                                # Handle renaming if needed
                                if new_profile_name != edit_profile_name:
                                    # Create new profile with new name
                                    if profile_manager.create_episode_profile(new_profile_name, updated_profile_data):
                                        # Delete old profile
                                        if profile_manager.delete_episode_profile(edit_profile_name):
                                            st.success(f"✅ 已将配置从 '{edit_profile_name}' 重命名为 '{new_profile_name}' 并更新成功！")
                                        else:
                                            st.warning(f"✅ 新配置 '{new_profile_name}' 已创建，但删除旧配置 '{edit_profile_name}' 失败。")
                                    else:
                                        st.error("❌ 创建重命名后的配置失败")
                                else:
                                    # Update existing profile
                                    if profile_manager.update_episode_profile(edit_profile_name, updated_profile_data):
                                        st.success(f"✅ 配置 '{edit_profile_name}' 更新成功！")
                                    else:
                                        st.error("❌ 更新配置失败")
                                
                                st.session_state.edit_episode_profile = None
                                st.rerun()
                
                with col2:
                    if st.button("❌ 取消编辑", key="cancel_edit_episode"):
                        st.session_state.edit_episode_profile = None
                        st.rerun()
                
                st.markdown("---")
            else:
                st.error(f"未找到剧集配置 '{edit_profile_name}'")
                st.session_state.edit_episode_profile = None
                st.rerun()
        
        # Display existing profiles
        st.subheader("已有剧集配置")
        
        if profile_names:
            # Display as grid
            cols = st.columns(3)
            
            for i, profile_name in enumerate(profile_names):
                profile_data = profiles["profiles"][profile_name]
                
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"### 📺 {profile_name}")
                        st.markdown(f"**说话人配置：** {profile_data.get('speaker_config', 'N/A')}")
                        st.markdown(f"**分段数：** {profile_data.get('num_segments', 'N/A')}")
                        
                        outline_provider = profile_data.get('outline_provider', 'ollama')
                        outline_model = profile_data.get('outline_model', 'N/A')
                        st.markdown(f"**大纲：** {outline_provider}/{outline_model}")
                        
                        transcript_provider = profile_data.get('transcript_provider', 'ollama')
                        transcript_model = profile_data.get('transcript_model', 'N/A')
                        st.markdown(f"**对话稿：** {transcript_provider}/{transcript_model}")

                        profile_language = profile_data.get('language')
                        if profile_language:
                            st.markdown(f"**语言：** {profile_language}")

                        # Action buttons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✏️ 编辑", key=f"edit_ep_{profile_name}", use_container_width=True):
                                st.session_state.edit_episode_profile = profile_name
                                st.rerun()
                        
                        with col2:
                            if st.button("📋 克隆", key=f"clone_ep_{profile_name}", use_container_width=True):
                                new_name = profile_manager.allocate_clone_name(profile_name, for_episode=True)
                                if profile_manager.clone_episode_profile(profile_name, new_name):
                                    st.success(f"✅ 已克隆为 '{new_name}'")
                                    st.rerun()
                                else:
                                    st.error("❌ 克隆失败")
                        
                        # Export button
                        export_data = profile_manager.export_episode_profiles([profile_name])
                        st.download_button(
                            label="💾 导出",
                            data=json.dumps(export_data, indent=2),
                            file_name=f"{profile_name}_episode_config.json",
                            mime="application/json",
                            key=f"export_ep_{profile_name}",
                            use_container_width=True
                        )
                        
                        # Delete button
                        if st.button("🗑️ 删除", key=f"delete_ep_{profile_name}", use_container_width=True):
                            if profile_manager.delete_episode_profile(profile_name):
                                st.success(f"✅ 已删除 '{profile_name}'")
                                st.rerun()
                            else:
                                st.error("❌ 删除失败")
                        
                        # Show more details in expander
                        with st.expander("📋 详情"):
                            st.markdown(f"**大纲提供商：** {profile_data.get('outline_provider', 'ollama')}")
                            st.markdown(f"**大纲模型：** {profile_data.get('outline_model', 'N/A')}")
                            st.markdown(f"**对话稿提供商：** {profile_data.get('transcript_provider', 'ollama')}")
                            st.markdown(f"**对话稿模型：** {profile_data.get('transcript_model', 'N/A')}")
                            st.markdown(f"**语言：** {profile_data.get('language', '默认（英文）')}")
                            st.markdown("**默认提示词：**")
                            st.text(profile_data.get('default_briefing', '未设置提示词'))
        else:
            st.info("还没有剧集配置，先创建一个吧。")
    
    except Exception as e:
        st.error(f"加载剧集配置失败：{str(e)}")
        st.markdown("请检查配置文件后重试。")

def show_generate_podcast_page():
    """Display the podcast generation page."""
    st.subheader("🎬 生成播客")
    st.markdown("创建新的播客剧集")
    
    # Initialize managers
    profile_manager = ProfileManager(working_dir=WORKING_DIR)
    episode_manager = EpisodeManager(base_output_dir=WORKING_DIR / "output")
    
    try:
        # Load available profiles
        episode_profiles = profile_manager.get_episode_profile_names()
        speaker_profiles = profile_manager.get_speaker_profile_names()
        
        if not episode_profiles:
            st.error("⚠️ 未找到剧集配置，请先创建。")
            if st.button("📺 前往剧集配置"):
                _set_current_page("episode_profiles")
                st.rerun()
            return
        
        if not speaker_profiles:
            st.error("⚠️ 未找到说话人配置（speakers_config.json 无 profiles）。请先创建或检查工作目录。")
            if st.button("🎙️ 前往说话人配置"):
                _set_current_page("speaker_profiles")
                st.rerun()
            return
        
        # Content input section
        st.markdown("### 第一步：内容收集")
        
        # Initialize session state for content pieces
        if 'content_pieces' not in st.session_state:
            st.session_state.content_pieces = []
        
        # Add new content section
        with st.expander("➕ 添加内容", expanded=len(st.session_state.content_pieces) == 0):
            content_source = st.radio(
                "内容来源：",
                ["文本输入", "文件上传", "URL"],
                horizontal=True,
                key="new_content_source"
            )
            
            if content_source == "文本输入":
                text_content = st.text_area("输入内容：", height=150, placeholder="请粘贴你的内容...", key="new_text_input")
                
                if st.button("📝 添加文本内容", disabled=not text_content.strip()):
                    if text_content.strip():
                        content_piece = {
                            'type': 'text',
                            'title': f"文本内容 {len(st.session_state.content_pieces) + 1}",
                            'content': text_content.strip(),
                            'source': '直接输入'
                        }
                        st.session_state.content_pieces.append(content_piece)
                        st.rerun()
            
            elif content_source == "文件上传":
                uploaded_file = st.file_uploader(
                    "上传文件：", 
                    type=['txt', 'pdf', 'docx', 'md', 'json'],
                    help="支持格式：TXT、PDF、DOCX、MD、JSON",
                    key="new_file_uploader"
                )
                
                if uploaded_file is not None and st.button("📄 添加文件内容"):
                    try:
                        if ContentExtractor.is_content_core_available():
                            with st.spinner("正在提取文件内容..."):
                                extracted_content = ContentExtractor.extract_from_uploaded_file(uploaded_file)
                                content_piece = {
                                    'type': 'file',
                                    'title': uploaded_file.name,
                                    'content': extracted_content,
                                    'source': f"File: {uploaded_file.name}"
                                }
                                st.session_state.content_pieces.append(content_piece)
                                st.success(f"✅ 已添加来自 {uploaded_file.name} 的内容")
                                st.rerun()
                        else:
                            st.error("⚠️ content-core 库不可用，请先安装：`pip install content-core`")
                    except Exception as e:
                        st.error(f"❌ 提取内容失败：{str(e)}")
            
            else:  # URL
                url = st.text_input("输入 URL：", placeholder="https://example.com/article", key="new_url_input")
                
                if url and st.button("🔗 添加 URL 内容"):
                    if ContentExtractor.validate_url(url):
                        try:
                            if ContentExtractor.is_content_core_available():
                                with st.spinner("正在提取 URL 内容..."):
                                    extracted_content = run_async_in_streamlit(ContentExtractor.extract_from_url, url)
                                    content_piece = {
                                        'type': 'url',
                                        'title': url,
                                        'content': extracted_content,
                                        'source': f"URL: {url}"
                                    }
                                    st.session_state.content_pieces.append(content_piece)
                                    st.success("✅ 已添加 URL 内容")
                                    st.rerun()
                            else:
                                st.error("⚠️ content-core 库不可用，请先安装：`pip install content-core`")
                        except Exception as e:
                            ErrorHandler.handle_streamlit_error(e, {"url": url})
                    else:
                        st.error("❌ URL 无效或无法访问")
        
        # Display content pieces
        if st.session_state.content_pieces:
            st.markdown("### 内容片段")

            for i, piece in enumerate(st.session_state.content_pieces):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        # Show content piece info
                        type_icon = {"text": "📝", "file": "📄", "url": "🔗"}.get(piece['type'], "📄")
                        st.markdown(f"**{type_icon} {piece['title']}**")
                        st.markdown(f"*来源：{piece['source']}*")
                        
                        # Content stats
                        piece_stats = ContentExtractor.get_content_stats(piece['content'])
                        st.markdown(f"📊 {piece_stats['character_count']} 字符，{piece_stats['word_count']} 词")
                        
                        # Preview
                        with st.expander("👀 预览"):
                            preview = ContentExtractor.truncate_content(piece['content'], 300)
                            st.text(preview)
                    
                    with col2:
                        # Move up/down buttons
                        if i > 0:
                            if st.button("⬆️", key=f"move_up_{i}", help="上移"):
                                st.session_state.content_pieces[i], st.session_state.content_pieces[i-1] = st.session_state.content_pieces[i-1], st.session_state.content_pieces[i]
                                st.rerun()
                        
                        if i < len(st.session_state.content_pieces) - 1:
                            if st.button("⬇️", key=f"move_down_{i}", help="下移"):
                                st.session_state.content_pieces[i], st.session_state.content_pieces[i+1] = st.session_state.content_pieces[i+1], st.session_state.content_pieces[i]
                                st.rerun()
                    
                    with col3:
                        # Delete button
                        if st.button("🗑️", key=f"delete_content_{i}", help="删除"):
                            st.session_state.content_pieces.pop(i)
                            st.rerun()

            # Actions
            if st.button("🔄 清空全部内容", type="secondary"):
                st.session_state.content_pieces = []
                st.rerun()
            
            # Set content for generation (pass array instead of concatenated string)
            content_pieces = st.session_state.content_pieces
        else:
            st.info("📝 还没有添加内容，请在上方“添加内容”区域加入文本、文件或 URL。")
            content_pieces = []
        
        st.markdown("---")
        
        # Configuration section
        st.markdown("### 第二步：参数配置")
        _prof_stats = profile_manager.get_profiles_stats()
        st.caption(
            f"配置根目录：**`{WORKING_DIR}`** · "
            f"已加载 **{_prof_stats['episode_profiles_count']}** 条剧集配置、"
            f"**{_prof_stats['speaker_profiles_count']}** 条说话人配置"
            f"（全部 profile 内说话人角色合计 **{_prof_stats['total_speakers']}** 个，可与首页统计对照）。"
            " 与管理页同源；子目录启动时会向上查找含两份 JSON 的目录。"
        )

        if "episode_profile_select" not in st.session_state:
            if "local_default" in episode_profiles:
                st.session_state.episode_profile_select = "local_default"
            elif "solo_expert_quality_local" in episode_profiles:
                st.session_state.episode_profile_select = "solo_expert_quality_local"
            elif episode_profiles:
                st.session_state.episode_profile_select = episode_profiles[0]

        def _on_episode_profile_changed() -> None:
            ep = st.session_state.episode_profile_select
            pd_local = profile_manager.get_episode_profile(ep)
            sc = (pd_local or {}).get("speaker_config")
            if sc and speaker_profiles and sc in speaker_profiles:
                st.session_state.speaker_profile_select = sc

        col_ep, col_sp = st.columns(2)
        with col_ep:
            episode_profile = st.selectbox(
                "剧集配置：",
                episode_profiles,
                help="与「剧集配置」页面列表一致",
                key="episode_profile_select",
                on_change=_on_episode_profile_changed,
            )
        with col_sp:
            if "speaker_profile_select" not in st.session_state:
                pd_init = profile_manager.get_episode_profile(episode_profile)
                sc_init = (pd_init or {}).get("speaker_config")
                st.session_state.speaker_profile_select = (
                    sc_init
                    if sc_init in speaker_profiles
                    else (speaker_profiles[0] if speaker_profiles else "")
                )
            st.selectbox(
                "说话人配置：",
                speaker_profiles,
                help="与「说话人配置」页面一致。切换剧集时自动对齐 JSON 中的 speaker_config，可再改选。",
                key="speaker_profile_select",
            )

        speaker_config = st.session_state.get("speaker_profile_select") or (
            speaker_profiles[0] if speaker_profiles else ""
        )

        use_defaults = st.checkbox(
            "使用配置默认值",
            value=True,
            key="use_profile_defaults",
            help="开启时模型、分段数等沿用剧集 JSON；说话人以上方下拉框为准。",
        )

        profile_data = profile_manager.get_episode_profile(episode_profile)
        
        briefing = ""
        briefing_suffix = ""
        outline_model = "qwen3:8b"
        transcript_model = "qwen3:8b"
        num_segments = 4

        if profile_data:
            st.markdown(f"**配置说明：** {profile_data.get('default_briefing', '无描述')}")
            st.markdown(
                f"**该剧集在 JSON 中绑定的说话人：** `{profile_data.get('speaker_config', 'N/A')}` "
                "（实际生成使用上方「说话人配置」所选名称）"
            )

            if not use_defaults:
                with st.expander("🔧 覆盖设置（模型 / 分段 / 提示词）", expanded=True):
                    outline_model = st.text_input(
                        "大纲模型：",
                        value=profile_data.get('outline_model', 'qwen3:8b')
                    )
                    transcript_model = st.text_input(
                        "对话稿模型：",
                        value=profile_data.get('transcript_model', 'qwen3:8b')
                    )
                    num_segments = st.slider(
                        "分段数量：",
                        1, 10,
                        value=profile_data.get('num_segments', 4)
                    )
                    briefing = st.text_area(
                        "提示词：",
                        value=profile_data.get('default_briefing', ''),
                        height=100
                    )
                    briefing_suffix = st.text_input(
                        "提示词补充：",
                        placeholder="补充额外要求..."
                    )
            else:
                outline_model = profile_data.get('outline_model', 'qwen3:8b')
                transcript_model = profile_data.get('transcript_model', 'qwen3:8b')
                num_segments = profile_data.get('num_segments', 4)
                briefing = profile_data.get('default_briefing', '')
                briefing_suffix = ""

            language = st.text_input(
                "语言：",
                value=profile_data.get('language', ''),
                placeholder="例如：zh-CN、pt-BR、es（留空默认英文）",
                key="generation_language",
                help="播客生成语言代码，支持 ISO 639-1（如 `zh`）或 BCP 47（如 `zh-CN`）。"
            )
        else:
            st.error(f"未找到剧集配置「{episode_profile}」，请检查 episodes_config.json。")
            language = st.text_input(
                "语言：",
                value="",
                placeholder="例如：zh-CN、pt-BR、es（留空默认英文）",
                key="generation_language",
                help="播客生成语言代码。",
            )

        st.markdown("---")
        
        # Briefing editor section
        st.markdown("### 第三步：提示词编辑")
        
        # Initialize briefing in session state if not exists or if profile changed
        if 'custom_briefing' not in st.session_state or 'last_episode_profile' not in st.session_state:
            st.session_state.custom_briefing = briefing
            st.session_state.last_episode_profile = episode_profile
        elif st.session_state.last_episode_profile != episode_profile:
            # Profile changed, update briefing
            st.session_state.custom_briefing = briefing
            st.session_state.last_episode_profile = episode_profile
        
        # Always show briefing editor
        col1, col2 = st.columns([3, 1])
        with col1:
            custom_briefing = st.text_area(
                "编辑提示词：",
                value=st.session_state.custom_briefing,
                height=120,
                help="编辑将发送给 AI 的生成提示词",
                key="custom_briefing_editor"
            )
        with col2:
            if st.button("🔄 恢复默认", key="reset_briefing"):
                st.session_state.custom_briefing = briefing
                st.rerun()
        
        # Update session state
        st.session_state.custom_briefing = custom_briefing
        
        # Show briefing preview
        if custom_briefing:
            with st.expander("📋 提示词预览"):
                st.markdown("**最终发送给 AI 的提示词：**")
                final_briefing = custom_briefing
                if not use_defaults and briefing_suffix:
                    final_briefing += f"\n\n{briefing_suffix}"
                st.text(final_briefing)
        
        st.markdown("---")
        
        # Output settings section
        st.markdown("### 第四步：输出设置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            episode_name = st.text_input(
                "剧集名称：",
                placeholder="my_awesome_podcast",
                help="将作为输出文件夹名称"
            )
        
        with col2:
            output_dir = st.text_input(
                "输出目录：",
                value="output",
                help="播客输出的根目录"
            )

        with st.expander("🎵 背景音乐（可选）", expanded=False):
            st.caption(
                "在合成最终 MP3 时叠混背景音乐：片头模式仅覆盖开场一段时间（类似新闻提要）；全程模式垫底整集。"
                "需使用本机音频文件（mp3/wav 等，与 pydub 兼容）。"
            )
            st.selectbox(
                "BGM 模式",
                options=list(_STUDIO_BGM_OPTIONS),
                index=0,
                key="studio_bgm_mode",
                help="选择「关闭」则不叠混。",
            )
            st.text_input(
                "BGM 文件路径",
                value="",
                placeholder="相对配置目录或绝对路径，例如 assets/bgm.mp3",
                key="studio_bgm_path",
            )
            st.slider(
                "片头 BGM 时长（秒）",
                min_value=3,
                max_value=60,
                value=12,
                key="studio_bgm_intro_sec",
                help="仅在「片头 BGM」模式下生效。",
            )
            st.slider(
                "BGM 相对音量（dB，数值越小越淡）",
                min_value=-36,
                max_value=-6,
                value=-20,
                key="studio_bgm_gain_db",
            )
        
        # Check if episode exists
        if episode_name:
            episode_exists = episode_manager.check_episode_exists(episode_name)
            if episode_exists:
                st.warning(f"⚠️ 剧集 '{episode_name}' 已存在，生成将覆盖已有文件。")
                overwrite_confirmed = st.checkbox("✅ 我已了解并确认覆盖", key="overwrite_confirm")
            else:
                overwrite_confirmed = True
        else:
            overwrite_confirmed = True
        
        st.markdown("---")
        
        # Generation section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Validate content pieces instead of concatenated content
            has_valid_content = bool(content_pieces and any(
                piece.get('content', '').strip() and len(piece.get('content', '').strip()) >= 50 
                for piece in content_pieces
            ))
            
            can_generate = (
                has_valid_content and 
                episode_name and 
                overwrite_confirmed
            )
            
            if not content_pieces:
                st.info("📝 请先添加内容片段，再开始生成播客")
            elif not has_valid_content:
                st.error("❌ 内容过短或无效。请至少提供一段 50 字以上的有效文本。")
            elif not episode_name:
                st.error("❌ 请填写剧集名称")
            elif not overwrite_confirmed:
                st.error("❌ 请勾选覆盖确认后继续")
        
        with col2:
            if st.button(
                "🎬 生成播客", 
                type="primary", 
                disabled=not can_generate,
                use_container_width=True
            ):
                st.session_state.start_generation = True
                st.rerun()
        
        # Handle podcast generation
        if st.session_state.get("start_generation", False):
            st.session_state.start_generation = False
            
            # Show generation progress
            progress_container = st.container()
            status_container = st.container()
            
            progress_bar = progress_container.progress(0)
            status_text = status_container.empty()
            
            try:
                status_text.text("🚀 开始生成播客...")
                progress_bar.progress(10)
                
                # Import podcast creator
                try:
                    from podcast_creator import create_podcast, configure
                    # Configure to use current working directory
                    configure("working_dir", str(WORKING_DIR))
                    podcast_creator_available = True
                except ImportError:
                    podcast_creator_available = False
                    st.error("❌ 未找到 podcast-creator 库，请先安装。")
                    return
                
                if podcast_creator_available:
                    status_text.text("📝 正在准备生成参数...")
                    progress_bar.progress(20)
                    
                    # Prepare parameters
                    generation_params = {
                        "content": [piece['content'] for piece in content_pieces],
                        "episode_name": episode_name,
                        "output_dir": f"{output_dir}/{episode_name}",
                        "episode_profile": episode_profile,
                        "speaker_config": speaker_config,
                    }

                    # Add language if specified
                    if language and language.strip():
                        generation_params["language"] = language.strip()

                    _bgm_label = st.session_state.get("studio_bgm_mode", "关闭")
                    _bgm_m = _STUDIO_BGM_MODE_BY_LABEL.get(_bgm_label)
                    _bgm_fp = (st.session_state.get("studio_bgm_path") or "").strip()
                    if _bgm_m and _bgm_fp:
                        _p = Path(_bgm_fp).expanduser()
                        if not _p.is_absolute():
                            _p = (WORKING_DIR / _p).resolve()
                        generation_params["bgm_path"] = str(_p)
                        generation_params["bgm_mode"] = _bgm_m
                        generation_params["bgm_intro_duration_ms"] = int(
                            st.session_state.get("studio_bgm_intro_sec", 12) * 1000
                        )
                        generation_params["bgm_gain_db"] = float(
                            st.session_state.get("studio_bgm_gain_db", -20)
                        )
                    elif _bgm_m and not _bgm_fp:
                        st.warning("已选择 BGM 模式但未填写文件路径，将不叠混背景音乐。")
                    
                    # Add overrides if not using defaults
                    if not use_defaults:
                        generation_params.update({
                            "outline_model": outline_model,
                            "transcript_model": transcript_model,
                            "num_segments": num_segments,
                            "briefing": st.session_state.custom_briefing
                        })
                        
                        if briefing_suffix:
                            generation_params["briefing_suffix"] = briefing_suffix
                    else:
                        # Even when using defaults, use the custom briefing if modified
                        if st.session_state.custom_briefing != briefing:
                            generation_params["briefing"] = st.session_state.custom_briefing
                    
                    status_text.text("🎙️ 正在生成播客，可能需要几分钟...")
                    progress_bar.progress(30)
                    
                    # Generate podcast
                    async def generate():
                        return await create_podcast(**generation_params)
                    
                    result = run_async_in_streamlit(generate)
                    
                    progress_bar.progress(100)
                    status_text.text("✅ 播客生成完成！")
                    
                    # Clear content after successful generation
                    st.session_state.generated_content = ""
                    st.session_state.content_stats = None
                    st.session_state.content_pieces = []
                    
                    # Show success message
                    st.success(f"🎉 播客 '{episode_name}' 生成成功！")
                    
                    if 'final_output_file_path' in result:
                        st.markdown(f"**音频文件：** `{result['final_output_file_path']}`")
                    
                    # Quick actions
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📚 前往剧集库", type="primary"):
                            _set_current_page("episode_library")
                            st.session_state.navigate_to_library = True
                            st.rerun()
                    
                    with col2:
                        if st.button("🎬 再生成一条"):
                            st.rerun()
                    
                    # Clean up progress indicators
                    progress_bar.empty()
                    status_text.empty()
            
            except Exception as e:
                # Clean up progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Handle the error
                total_content_length = sum(len(piece.get('content', '')) for piece in content_pieces) if content_pieces else 0
                ErrorHandler.handle_streamlit_error(e, {
                    "episode_name": episode_name,
                    "episode_profile": episode_profile,
                    "content_pieces_count": len(content_pieces) if content_pieces else 0,
                    "total_content_length": total_content_length
                })
                
                # Show retry button
                if st.button("🔄 重试生成", type="primary"):
                    st.session_state.start_generation = True
                    st.rerun()
    
    except Exception as e:
        st.error(f"加载生成页面失败：{str(e)}")
        st.markdown("请检查配置后重试。")

def show_episode_library_page():
    """Display the episode library and playback page."""
    st.subheader("📚 剧集库")
    st.markdown("浏览并播放已生成的剧集")
    
    # Initialize episode manager
    episode_manager = EpisodeManager(base_output_dir=WORKING_DIR / "output")
    
    try:
        # Load episodes
        all_episodes = episode_manager.scan_episodes_directory()
        
        if not all_episodes:
            st.info("📝 暂无剧集，先生成你的第一期播客吧！")
            if st.button("🎬 生成第一期播客", type="primary"):
                _set_current_page("generate_podcast")
                st.rerun()
            return
        
        # Search and filter controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input("🔍 搜索剧集：", placeholder="按名称搜索...")
        
        with col2:
            sort_by = st.selectbox("排序方式：", ["最新优先", "最旧优先", "名称 A-Z", "时长"])
        
        with col3:
            view_mode = st.radio("视图：", ["网格", "列表"], horizontal=True)
        
        # Filter and sort episodes
        filtered_episodes = episode_manager.search_episodes(search_query, all_episodes)
        sorted_episodes = episode_manager.sort_episodes(filtered_episodes, sort_by)
        
        # Show episode count
        st.markdown(f"**共找到 {len(sorted_episodes)} 个剧集**")
        st.markdown("---")
        
        # Handle selected episode for playback
        selected_episode = st.session_state.get("selected_episode")
        
        # Episode playback section
        if selected_episode and selected_episode.audio_file:
            with st.container(border=True):
                st.markdown(f"### 🎵 正在播放：{selected_episode.name}")
                
                # Audio player
                if Path(selected_episode.audio_file).exists():
                    audio_file = open(selected_episode.audio_file, 'rb')
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format='audio/mp3')
                    audio_file.close()
                    
                    # Episode details
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        _playback_dur = selected_episode.duration
                        if _playback_dur is None and selected_episode.audio_file:
                            _playback_dur = episode_manager.get_audio_duration(
                                selected_episode.audio_file
                            )
                        if _playback_dur:
                            st.metric("时长", episode_manager.format_duration(_playback_dur))
                    
                    with col2:
                        if selected_episode.speakers_count:
                            st.metric("说话人数", selected_episode.speakers_count)
                    
                    with col3:
                        if selected_episode.file_size:
                            st.metric("文件大小", episode_manager.format_file_size(selected_episode.file_size))
                    
                    # Action buttons
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("📄 查看对话稿", use_container_width=True):
                            st.session_state.show_transcript = True
                            st.rerun()
                    
                    with col2:
                        if st.button("📊 查看大纲", use_container_width=True):
                            st.session_state.show_outline = True
                            st.rerun()
                    
                    with col3:
                        # Download button
                        if st.download_button(
                            label="⬇️ 下载",
                            data=audio_bytes,
                            file_name=f"{selected_episode.name}.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        ):
                            st.success("📥 已开始下载")
                    
                    with col4:
                        if st.button("🗑️ 删除", use_container_width=True):
                            st.session_state.confirm_delete = selected_episode.name
                            st.rerun()
                else:
                    st.error("❌ 未找到音频文件")
                
                # Show transcript
                if st.session_state.get("show_transcript", False):
                    if selected_episode.transcript_file and Path(selected_episode.transcript_file).exists():
                        with st.expander("📄 对话稿", expanded=True):
                            try:
                                with open(selected_episode.transcript_file, 'r', encoding='utf-8') as f:
                                    transcript_data = json.load(f)
                                
                                if isinstance(transcript_data, list):
                                    for i, segment in enumerate(transcript_data):
                                        if isinstance(segment, dict):
                                            speaker = segment.get('speaker', f'说话人 {i+1}')
                                            # Try multiple possible field names for the text content
                                            text = (segment.get('text') or 
                                                   segment.get('content') or 
                                                   segment.get('dialogue') or 
                                                   segment.get('message') or 
                                                   segment.get('speech') or '')
                                            
                                            # Debug: Show available keys if text is empty
                                            if not text and st.session_state.get('debug_transcript', False):
                                                st.warning(f"调试 - 第 {i+1} 段字段：{list(segment.keys())}")
                                                st.json(segment)
                                            
                                            if text:
                                                st.markdown(f"**{speaker}:** {text}")
                                                st.markdown("---")
                                            else:
                                                st.markdown(f"**{speaker}:** *[未找到内容]*")
                                                st.markdown("---")
                                else:
                                    st.text(str(transcript_data))
                                
                                # Add debug toggle
                                if st.checkbox("🐛 调试模式 - 显示原始数据", key="debug_transcript_toggle"):
                                    st.session_state.debug_transcript = True
                                    st.json(transcript_data)
                                else:
                                    st.session_state.debug_transcript = False
                            except Exception as e:
                                st.error(f"加载对话稿失败：{str(e)}")
                            
                            if st.button("❌ 关闭对话稿"):
                                st.session_state.show_transcript = False
                                st.rerun()
                    else:
                        st.error("❌ 未找到对话稿文件")
                
                # Show outline
                if st.session_state.get("show_outline", False):
                    if selected_episode.outline_file and Path(selected_episode.outline_file).exists():
                        with st.expander("📊 大纲", expanded=True):
                            try:
                                with open(selected_episode.outline_file, 'r', encoding='utf-8') as f:
                                    outline_data = json.load(f)
                                st.json(outline_data)
                            except Exception as e:
                                st.error(f"加载大纲失败：{str(e)}")
                            
                            if st.button("❌ 关闭大纲"):
                                st.session_state.show_outline = False
                                st.rerun()
                    else:
                        st.error("❌ 未找到大纲文件")
                
                # Stop playback button
                if st.button("⏹️ 停止播放"):
                    st.session_state.selected_episode = None
                    st.session_state.show_transcript = False
                    st.session_state.show_outline = False
                    st.rerun()
            
            st.markdown("---")
        
        # Handle delete confirmation
        if st.session_state.get("confirm_delete"):
            episode_to_delete = st.session_state.confirm_delete
            
            st.warning(f"⚠️ 你确定要删除剧集 '{episode_to_delete}' 吗？")
            st.markdown("此操作不可撤销，将永久删除该剧集的所有文件。")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ 确认删除", type="primary"):
                    # Find the episode to delete
                    for episode in sorted_episodes:
                        if episode.name == episode_to_delete:
                            if episode_manager.delete_episode(episode.path):
                                st.success(f"✅ 剧集 '{episode_to_delete}' 已删除")
                                if st.session_state.get("selected_episode") and st.session_state.selected_episode.name == episode_to_delete:
                                    st.session_state.selected_episode = None
                                st.session_state.confirm_delete = None
                                st.rerun()
                            else:
                                st.error("❌ 删除剧集失败")
                            break
            
            with col2:
                if st.button("❌ 取消"):
                    st.session_state.confirm_delete = None
                    st.rerun()
            
            st.markdown("---")
        
        # Display episodes
        if view_mode == "网格":
            # Grid view
            cols = st.columns(3)
            
            for i, episode in enumerate(sorted_episodes):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"### 🎙️ {episode.name}")
                        
                        if episode.created_date:
                            st.markdown(f"**创建时间：** {episode.created_date.strftime('%Y-%m-%d %H:%M')}")
                        
                        if episode.duration:
                            st.markdown(f"**时长：** {episode_manager.format_duration(episode.duration)}")
                        
                        if episode.speakers_count:
                            st.markdown(f"**说话人数：** {episode.speakers_count}")
                        
                        if episode.profile_used:
                            st.markdown(f"**配置：** {episode.profile_used}")
                        
                        # Action buttons
                        if episode.audio_file and st.button("▶️ 播放", key=f"play_grid_{i}", use_container_width=True):
                            st.session_state.selected_episode = episode
                            st.rerun()
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if episode.transcript_file and st.button("📄", key=f"transcript_grid_{i}", help="查看对话稿"):
                                st.session_state.selected_episode = episode
                                st.session_state.show_transcript = True
                                st.rerun()
                        
                        with col2:
                            if st.button("🗑️", key=f"delete_grid_{i}", help="删除剧集"):
                                st.session_state.confirm_delete = episode.name
                                st.rerun()
        
        else:
            # List view
            for i, episode in enumerate(sorted_episodes):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"### 🎙️ {episode.name}")
                        if episode.created_date:
                            st.markdown(f"*创建时间：{episode.created_date.strftime('%Y-%m-%d %H:%M')}*")
                    
                    with col2:
                        info_lines = []
                        if episode.duration:
                            info_lines.append(f"时长：{episode_manager.format_duration(episode.duration)}")
                        if episode.speakers_count:
                            info_lines.append(f"说话人数：{episode.speakers_count}")
                        if episode.profile_used:
                            info_lines.append(f"配置：{episode.profile_used}")
                        
                        for line in info_lines:
                            st.markdown(line)
                    
                    with col3:
                        if episode.audio_file and st.button("▶️ 播放", key=f"play_list_{i}"):
                            st.session_state.selected_episode = episode
                            st.rerun()
                        
                        if episode.transcript_file and st.button("📄 对话稿", key=f"transcript_list_{i}"):
                            st.session_state.selected_episode = episode
                            st.session_state.show_transcript = True
                            st.rerun()
                        
                        if st.button("🗑️ 删除", key=f"delete_list_{i}"):
                            st.session_state.confirm_delete = episode.name
                            st.rerun()
        
        # Library statistics
        if sorted_episodes:
            with st.expander("📊 剧集库统计", expanded=False):
                st.caption(
                    "列表默认不批量读时长；"
                    "单集详情用 ffprobe → mutagen → pydub 取时长（ffprobe 需 FFmpeg；mutagen 在安装 ui 额外依赖时可用）。"
                    "快速扫描下总时长/平均时长常为 0。"
                )
                stats = episode_manager.get_episodes_stats()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("剧集总数", stats['total_episodes'])
                
                with col2:
                    if stats['total_duration'] > 0:
                        total_hours = stats['total_duration'] / 3600
                        st.metric("总时长", f"{total_hours:.1f} 小时")
                
                with col3:
                    if stats['average_duration'] > 0:
                        st.metric("平均时长", episode_manager.format_duration(stats['average_duration']))
                
                with col4:
                    if stats['total_size'] > 0:
                        st.metric("总大小", episode_manager.format_file_size(stats['total_size']))
    
    except Exception as e:
        st.error(f"加载剧集库失败：{str(e)}")
        st.markdown("请检查输出目录后重试。")

if __name__ == "__main__":
    main()