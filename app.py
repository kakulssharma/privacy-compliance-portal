import streamlit as st
import tenseal as ts
import pandas as pd
import sqlite3
import hashlib
import os
import json
import subprocess

# --- 1. DATABASE SETUP ---
# This creates a 'compliance.db' file in your folder automatically
def get_db_connection():
    conn = sqlite3.connect('data/compliance.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    # Table for storing encrypted data from different institutions
    conn.execute('''CREATE TABLE IF NOT EXISTS ledger 
                    (common_id TEXT, institution TEXT, encrypted_blob BLOB)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. CRYPTO HELPERS ---
def create_ctx():
    ctx = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=8192, plain_modulus=1032193)
    ctx.generate_galois_keys()
    return ctx

def get_hash(pii):
    return hashlib.sha256((str(pii) + "VIVA_SALT_2026").encode()).hexdigest()[:12]

# --- 3. UI SETUP ---
st.set_page_config(page_title="Privacy Portal", layout="centered")

# Sidebar for Login
st.sidebar.title("🔐 Login Portal")
identity = st.sidebar.selectbox("Access as:", ["Bank of America", "HDFC Bank", "Regulator (VIVA Admin)"])

if identity == "Regulator (VIVA Admin)":
    st.title("🛡️ Regulator Control Center")
    threshold = st.number_input("Set Global Risk Threshold ($)", value=50000)
    search_id = st.text_input("Enter Hashed ID to Audit")
    
    if st.button("Run ZK-Privacy Audit"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_blob FROM ledger WHERE common_id=?", (search_id,))
        results = cursor.fetchall()
        
        if results:
            with st.spinner("Aggregating Ciphertexts..."):
                ctx = create_ctx()
                # HE Aggregation logic
                all_ciphers = [ts.bfv_vector_from(ctx, r[0]) for r in results]
                final_sum_cipher = all_ciphers[0]
                for i in range(1, len(all_ciphers)):
                    final_sum_cipher += all_ciphers[i]
                
                # Decrypt and run ZK
                total_val = int(final_sum_cipher.decrypt()[0])
                
                # Create ZK Input
                zk_in = {"global_total": str(total_val), "risk_threshold": str(threshold)}
                with open("zkp/input.json", "w") as f: json.dump(zk_in, f)
                
                # Run your existing ZK commands
                try:
                    subprocess.run(f"node zkp/final_eligibility_js/generate_witness.js zkp/final_eligibility_js/final_eligibility.wasm zkp/input.json zkp/witness.wtns", shell=True, check=True)
                    subprocess.run(f"snarkjs groth16 prove zkp/circuit.zkey zkp/witness.wtns zkp/proof.json zkp/public.json", shell=True, check=True)
                    st.success(f"✅ COMPLIANT: Aggregate is under limit.")
                    st.balloons()
                except:
                    st.error("🚨 FRAUD ALERT: Threshold Exceeded!")
        else:
            st.warning("No data found for this ID.")

else:
    # DATA PROVIDER UI (For the hospitals/banks)
    st.title(f"🏥 {identity} Data Portal")
    user_id = st.text_input("Patient/Customer ID")
    uploaded_file = st.file_uploader("Upload Daily Transactions (CSV)", type="csv")
    
    if uploaded_file and st.button("Encrypt & Submit to Global Ledger"):
        df = pd.read_csv(uploaded_file)
        val = int(df['amount'].sum())
        
        # Encrypt
        ctx = create_ctx()
        enc_val = ts.bfv_vector(ctx, [val]).serialize()
        hashed_id = get_hash(user_id)
        
        # Save to SQLite Database
        conn = get_db_connection()
        conn.execute("INSERT INTO ledger VALUES (?, ?, ?)", (hashed_id, identity, enc_val))
        conn.commit()
        
        st.success(f"Data for {hashed_id} encrypted and synced to database!")