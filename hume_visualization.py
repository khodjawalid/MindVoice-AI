"""
Hume Emotion Visualization Dashboard

Interactive Streamlit app to visualize Hume AI Expression Measurement results:
- Face emotions (48 dimensions)
- Prosody/voice emotions (48 dimensions)
- Fused 9-emotion predictions

Usage:
    streamlit run hume_visualization.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import json
import os
from datetime import datetime

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Supabase client
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Video directory
VIDEOS_DIR = Path(__file__).parent / "backend" / "videos"

st.set_page_config(
    page_title="MindVoice - Hume Emotion Analysis",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 MindVoice - Hume AI Emotion Analysis")
st.markdown("Visualize facial expressions and voice prosody emotions from daily check-ins")


def get_daily_inferences():
    """Fetch all daily video inferences from Supabase."""
    result = supabase.table("daily_video_inferences").select("*").order("record_date", desc=True).execute()
    return result.data


def plot_emotion_radar(emotions: dict, title: str, color: str = "blue"):
    """Create a radar chart for emotions."""
    if not emotions:
        return None
    
    # Sort by value and take top 12 for readability
    sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:12]
    labels = [e[0] for e in sorted_emotions]
    values = [e[1] for e in sorted_emotions]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],  # Close the polygon
        theta=labels + [labels[0]],
        fill='toself',
        name=title,
        line_color=color,
        fillcolor=color.replace(")", ", 0.3)").replace("rgb", "rgba") if "rgb" in color else color
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(values) * 1.1])
        ),
        showlegend=False,
        title=title,
        height=400
    )
    
    return fig


def plot_emotion_bars(emotions: dict, title: str, color: str):
    """Create horizontal bar chart for all emotions."""
    if not emotions:
        return None
    
    df = pd.DataFrame([
        {"emotion": k, "score": v} for k, v in emotions.items()
    ]).sort_values("score", ascending=True)
    
    fig = px.bar(
        df, 
        x="score", 
        y="emotion", 
        orientation="h",
        title=title,
        color_discrete_sequence=[color]
    )
    fig.update_layout(height=max(400, len(emotions) * 20))
    
    return fig


def plot_fused_emotions(probs: dict):
    """Create a pie chart for the 9 fused emotions."""
    df = pd.DataFrame([
        {"emotion": k, "probability": v} for k, v in probs.items()
    ]).sort_values("probability", ascending=False)
    
    colors = {
        "anger": "#e74c3c",
        "calm": "#3498db", 
        "contempt": "#9b59b6",
        "disgust": "#27ae60",
        "fear": "#f39c12",
        "happy": "#f1c40f",
        "neutral": "#95a5a6",
        "sad": "#34495e",
        "surprise": "#e91e63"
    }
    
    fig = px.pie(
        df,
        values="probability",
        names="emotion",
        title="Predicted Emotions (Fused)",
        color="emotion",
        color_discrete_map=colors
    )
    
    return fig


def main():
    # Sidebar
    st.sidebar.header("📅 Select Recording")
    
    inferences = get_daily_inferences()
    
    if not inferences:
        st.warning("No daily video inferences found. Record a daily check-in first!")
        st.info("Go to the Daily Check-in page in the frontend and record a video.")
        return
    
    # Date selector
    dates = [inf["record_date"] for inf in inferences]
    selected_date = st.sidebar.selectbox("Date", dates)
    
    # Get selected inference
    selected = next((inf for inf in inferences if inf["record_date"] == selected_date), None)
    
    if not selected:
        st.error("Inference not found")
        return
    
    # Display metadata
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Date", selected["record_date"])
    with col2:
        st.metric("Predicted Emotion", selected["predicted_emotion"].upper())
    with col3:
        st.metric("Confidence", f"{selected['pred_confidence']:.1%}")
    with col4:
        backend = selected.get("backend", "unknown")
        st.metric("Backend", backend.upper())
    
    st.divider()
    
    # Video player (if available)
    video_path = selected.get("video_path")
    if video_path and Path(video_path).exists():
        st.subheader("🎥 Recorded Video")
        st.video(video_path)
    
    # Fused emotions
    st.subheader("🎯 Final Emotion Prediction (9 Classes)")
    
    emotion_probs = selected.get("emotion_probabilities", {})
    if emotion_probs:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            fig = plot_fused_emotions(emotion_probs)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bar chart
            df = pd.DataFrame([
                {"Emotion": k.capitalize(), "Probability": v} 
                for k, v in emotion_probs.items()
            ]).sort_values("Probability", ascending=False)
            
            fig = px.bar(
                df, x="Emotion", y="Probability",
                color="Probability",
                color_continuous_scale="Viridis"
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Hume raw emotions (if available)
    raw_face = selected.get("raw_face_emotions", {})
    raw_prosody = selected.get("raw_prosody_emotions", {})
    
    if raw_face or raw_prosody:
        st.subheader("🔬 Hume AI Raw Emotions (48 Dimensions)")
        
        tab1, tab2, tab3 = st.tabs(["📊 Comparison", "😊 Face Details", "🎤 Prosody Details"])
        
        with tab1:
            # Side by side radar charts
            col1, col2 = st.columns(2)
            
            with col1:
                if raw_face:
                    fig = plot_emotion_radar(raw_face, "Face Emotions (Top 12)", "rgb(255, 99, 132)")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No face emotion data available")
            
            with col2:
                if raw_prosody:
                    fig = plot_emotion_radar(raw_prosody, "Prosody Emotions (Top 12)", "rgb(54, 162, 235)")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No prosody emotion data available")
            
            # Combined top emotions
            if raw_face and raw_prosody:
                st.subheader("🔀 Face vs Prosody Comparison")
                
                # Get top 15 emotions from each
                all_emotions = set(list(raw_face.keys())[:15] + list(raw_prosody.keys())[:15])
                
                comparison_data = []
                for emotion in all_emotions:
                    comparison_data.append({
                        "Emotion": emotion,
                        "Face": raw_face.get(emotion, 0),
                        "Prosody": raw_prosody.get(emotion, 0)
                    })
                
                df = pd.DataFrame(comparison_data).sort_values("Face", ascending=False).head(15)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Face", x=df["Emotion"], y=df["Face"], marker_color="rgb(255, 99, 132)"))
                fig.add_trace(go.Bar(name="Prosody", x=df["Emotion"], y=df["Prosody"], marker_color="rgb(54, 162, 235)"))
                fig.update_layout(barmode="group", height=400, title="Top Emotions: Face vs Prosody")
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            if raw_face:
                st.markdown("### All Face Emotions (48)")
                fig = plot_emotion_bars(raw_face, "Face Expression Emotions", "rgb(255, 99, 132)")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Data table
                with st.expander("📋 View Raw Data"):
                    df = pd.DataFrame([
                        {"Emotion": k, "Score": f"{v:.4f}"} 
                        for k, v in sorted(raw_face.items(), key=lambda x: x[1], reverse=True)
                    ])
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("No face emotion data available for this recording")
        
        with tab3:
            if raw_prosody:
                st.markdown("### All Prosody Emotions (48)")
                fig = plot_emotion_bars(raw_prosody, "Voice Prosody Emotions", "rgb(54, 162, 235)")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Data table
                with st.expander("📋 View Raw Data"):
                    df = pd.DataFrame([
                        {"Emotion": k, "Score": f"{v:.4f}"} 
                        for k, v in sorted(raw_prosody.items(), key=lambda x: x[1], reverse=True)
                    ])
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("No prosody emotion data available for this recording")
    
    else:
        st.info("💡 Raw Hume emotions not available. This recording may have used the local model backend.")
    
    # JSON export
    st.divider()
    with st.expander("🔧 Raw JSON Data"):
        st.json(selected)


if __name__ == "__main__":
    main()
