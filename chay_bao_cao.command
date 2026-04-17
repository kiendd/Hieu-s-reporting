#!/bin/bash
# Resolve script path — fix macOS dropping leading "/" when path has spaces
_src="${BASH_SOURCE[0]:-$0}"
[[ "$_src" != /* ]] && _src="/$_src"
cd "$(dirname "$_src")" || exit 1
streamlit run app.py
