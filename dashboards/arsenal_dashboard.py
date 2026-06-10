"""
Arsenal trends dashboard using Streamlit.

Read-only dashboard for viewing arsenal trends, shape clustering, usage shifts, and whiff zones.
"""

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import clean_trackman
from src.metrics import (
    generate_arsenal_summary,
    generate_plate_discipline_summary,
    generate_contact_summary,
)
from src.visualizations import plot_movement_scatter
from src.pitch_colors import get_pitch_color_map

if not STREAMLIT_AVAILABLE:
    print("Streamlit and Plotly are required for dashboards. Install with: pip install streamlit plotly")
    sys.exit(1)

st.set_page_config(
    page_title="Dirtbags Arsenal Dashboard",
    page_icon="⚾",
    layout="wide",
)

st.title("⚾ Dirtbags Arsenal Dashboard")
st.markdown("**Internal Use Only - Confidential**")

# File upload
uploaded_file = st.file_uploader("Upload Trackman CSV", type=['csv'])

if uploaded_file is not None:
    # Load and clean data
    df_raw = pd.read_csv(uploaded_file)
    df = clean_trackman(df_raw, strict=False)
    
    st.sidebar.header("Filters")
    pitch_types = st.sidebar.multiselect(
        "Select Pitch Types",
        options=df['pitch_type'].dropna().unique().tolist(),
        default=df['pitch_type'].dropna().unique().tolist(),
    )
    
    if pitch_types:
        df_filtered = df[df['pitch_type'].isin(pitch_types)]
    else:
        df_filtered = df

    pitch_color_map = get_pitch_color_map(df_filtered['pitch_type'].dropna().unique())
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Arsenal Summary", "Movement", "Plate Discipline", "Contact"])
    
    with tab1:
        st.header("Arsenal Summary")
        arsenal = generate_arsenal_summary(df_filtered)
        st.dataframe(arsenal, use_container_width=True)
        
        # Usage trends
        st.subheader("Usage by Pitch Type")
        usage_data = arsenal[['Pitch Type', 'Usage%', 'Pitches']]
        fig = px.bar(usage_data, x='Pitch Type', y='Usage%', title='Pitch Usage %')
        st.plotly_chart(fig, use_container_width=True)
        
        # Velocity trends
        st.subheader("Velocity by Pitch Type")
        vel_data = arsenal[['Pitch Type', 'Velocity AVG', 'Velocity MAX']]
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Average', x=vel_data['Pitch Type'], y=vel_data['Velocity AVG']))
        fig.add_trace(go.Bar(name='Maximum', x=vel_data['Pitch Type'], y=vel_data['Velocity MAX']))
        fig.update_layout(title='Velocity (mph)', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("Pitch Movement")
        
        # HB vs IVB scatter
        st.subheader("HB vs IVB Scatter")
        movement_data = df_filtered[['pitch_type', 'hb', 'ivb']].dropna()
        if len(movement_data) > 0:
            fig = px.scatter(
                movement_data,
                x='hb',
                y='ivb',
                color='pitch_type',
                color_discrete_map=pitch_color_map,
                title='Horizontal Break vs Induced Vertical Break',
                labels={'hb': 'Horizontal Break (inches)', 'ivb': 'Induced Vertical Break (inches)'},
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.add_vline(x=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
        
        # Spin rate by pitch type
        st.subheader("Spin Rate Distribution")
        spin_data = df_filtered[['pitch_type', 'spin_rate']].dropna()
        if len(spin_data) > 0:
            fig = px.box(
                spin_data,
                x='pitch_type',
                y='spin_rate',
                title='Spin Rate by Pitch Type',
                color='pitch_type',
                color_discrete_map=pitch_color_map,
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.header("Plate Discipline")
        plate_disc = generate_plate_discipline_summary(df_filtered)
        st.dataframe(plate_disc, use_container_width=True)
        
        # Whiff rates
        st.subheader("Whiff Rates")
        whiff_data = plate_disc[['Pitch Type', 'Whiff%', 'Z-Whiff%', 'O-Whiff%']]
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Overall', x=whiff_data['Pitch Type'], y=whiff_data['Whiff%']))
        fig.add_trace(go.Bar(name='Zone', x=whiff_data['Pitch Type'], y=whiff_data['Z-Whiff%']))
        fig.add_trace(go.Bar(name='Out of Zone', x=whiff_data['Pitch Type'], y=whiff_data['O-Whiff%']))
        fig.update_layout(title='Whiff Rates (%)', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("Contact Outcomes")
        contact = generate_contact_summary(df_filtered)
        st.dataframe(contact, use_container_width=True)
        
        # Contact type distribution
        st.subheader("Contact Type Distribution")
        contact_data = contact[['Pitch Type', 'GB%', 'FB%', 'LD%', 'PU%']]
        fig = go.Figure()
        for col in ['GB%', 'FB%', 'LD%', 'PU%']:
            fig.add_trace(go.Bar(name=col, x=contact_data['Pitch Type'], y=contact_data[col]))
        fig.update_layout(title='Contact Type Distribution (%)', barmode='stack')
        st.plotly_chart(fig, use_container_width=True)
        
        # Exit velocity
        st.subheader("Exit Velocity")
        ev_data = contact[['Pitch Type', 'EV AVG', 'EV MAX']]
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Average', x=ev_data['Pitch Type'], y=ev_data['EV AVG']))
        fig.add_trace(go.Bar(name='Maximum', x=ev_data['Pitch Type'], y=ev_data['EV MAX']))
        fig.update_layout(title='Exit Velocity (mph)', barmode='group')
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👆 Upload a Trackman CSV file to begin")

