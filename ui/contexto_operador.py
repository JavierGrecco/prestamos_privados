"""Contexto del operador declarado en la UI.

Este contexto identifica quién declara realizar una operación dentro de la
sesión de Streamlit. No es un mecanismo de autenticación ni de autorización.
"""
from __future__ import annotations

import os

import streamlit as st


def operador_por_defecto() -> str:
    valor = os.environ.get("PRESTAMOS_OPERADOR", "").strip()
    return valor or "admin"


def inicializar_operador() -> None:
    if "operador" not in st.session_state:
        st.session_state["operador"] = operador_por_defecto()
    if not str(st.session_state.get("operador", "")).strip():
        st.session_state["operador"] = operador_por_defecto()


def operador_actual() -> str:
    inicializar_operador()
    return str(st.session_state["operador"]).strip()
