"""
Interface Streamlit pour visualiser les données biologiques Empatica
Affiche les métriques clés et des graphiques pour EDA et Heart Rate
Met en évidence les moments où des tags ont été déclenchés
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# Configuration de la page
st.set_page_config(
    page_title="Visualisation Données Biologiques",
    page_icon="📊",
    layout="wide"
)

# Chargement des données
@st.cache_data
def load_data(csv_path):
    """Charge et prépare les données"""
    df = pd.read_csv(csv_path)
    df['datetime'] = pd.to_datetime(df['timestamp_iso'])
    
    # Convertir en numérique, exclure "device_not_recording"
    df['eda_numeric'] = pd.to_numeric(df['eda'], errors='coerce')
    df['heart_rate_numeric'] = pd.to_numeric(df['heart_rate'], errors='coerce')
    
    return df





def create_time_plot(df, column, title, ylabel, color):
    """Crée un graphique temporel avec mise en évidence des tags"""
    valid_data = df[df[f'{column}_numeric'].notna()].copy()
    
    if len(valid_data) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Aucune donnée {title} disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    fig = go.Figure()
    
    # Ligne principale
    fig.add_trace(go.Scatter(
        x=valid_data['datetime'],
        y=valid_data[f'{column}_numeric'],
        mode='lines+markers',
        name=title,
        line=dict(color=color, width=2),
        marker=dict(size=4),
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Date: %{x}<br>' +
                      'Valeur: %{y:.2f}<extra></extra>'
    ))
    
    # Mettre en évidence les tags
    tags_data = valid_data[valid_data['has_tag'] == 1]
    if len(tags_data) > 0:
        fig.add_trace(go.Scatter(
            x=tags_data['datetime'],
            y=tags_data[f'{column}_numeric'],
            mode='markers',
            name='Tag déclenché',
            marker=dict(
                size=15,
                color='red',
                symbol='x',
                line=dict(width=2, color='darkred')
            ),
            hovertemplate='<b>Tag déclenché</b><br>' +
                         'Date: %{x}<br>' +
                         'Valeur: %{y:.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text=f'{title} au fil du temps', font=dict(size=18)),
        xaxis_title='Heure de la journée',
        yaxis_title=ylabel,
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    return fig


def create_distribution_plot(df, column, title, xlabel, color):
    """Crée un graphique de distribution (histogramme)"""
    valid_data = df[df[f'{column}_numeric'].notna()].copy()
    
    if len(valid_data) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Aucune donnée {title} disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=valid_data[f'{column}_numeric'],
        nbinsx=30,
        name=f'Distribution {title}',
        marker_color=color,
        opacity=0.7,
        hovertemplate='<b>%{title}</b><br>' +
                      'Valeur: %{x:.2f}<br>' +
                      'Fréquence: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=f'Distribution des valeurs {title}', font=dict(size=18)),
        xaxis_title=xlabel,
        yaxis_title='Fréquence',
        template='plotly_white',
        height=400,
        showlegend=False
    )
    
    return fig


# Interface principale
st.title("📊 Visualisation des Données Biologiques Empatica")

# Chargement des données
default_path = "empatica_2026-01-16/processed/merged_data_2026-01-16.csv"
csv_path = st.sidebar.text_input("Chemin du fichier CSV", value=default_path)

df = load_data(csv_path)

st.plotly_chart(
    create_time_plot(df, 'eda', 'EDA', 'EDA (μSiemens)', '#1f77b4'),
    use_container_width=True
)
st.plotly_chart(
    create_time_plot(df, 'heart_rate', 'Heart Rate', 'Heart Rate (bpm)', '#2ca02c'),
    use_container_width=True
)

