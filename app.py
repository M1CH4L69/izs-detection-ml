import streamlit as st
from ultralytics import YOLO
from PIL import Image

st.set_page_config(
    page_title="IZS Detektor",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def load_model():
    try:
        return YOLO("best.pt")
    except:
        return YOLO("yolov8n.pt") 

model = load_model()

st.title("🚑 AI Detektor vozidel IZS")
st.markdown("""
Tato aplikace využívá **vlastní konvoluční neuronovou síť (YOLOv8)** natrénovanou k rozpoznávání tří typů vozidel:
* 🚒 **Hasiči**
* 🚓 **Policie**
* 🚑 **Záchranka**
""")

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Nahrajte fotografii")
    uploaded_file = st.file_uploader("Vyberte soubor (JPG, PNG)", type=["jpg", "jpeg", "png"])
    confidence_threshold = st.slider(
        "Confidence threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.01,
        help="Nižší hodnota = více detekcí, vyšší hodnota = přísnější detekce.",
    )

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    with col1:
        st.image(image, caption="Původní fotografie", use_container_width=True)
        
        analyze_button = st.button("Spustit AI Analýzu", type="primary", use_container_width=True)

    if analyze_button:
        with col2:
            st.subheader("2. Výsledek detekce")
            with st.spinner('Neuronová síť analyzuje pixely... 🧠'):
                
                results = model.predict(image, conf=confidence_threshold)
                res_plotted = results[0].plot() 
                
                st.image(res_plotted, caption="Detekovaná vozidla", use_container_width=True, channels="BGR")
                
                st.success("Analýza dokončena!")
                
                boxes = results[0].boxes
                if len(boxes) == 0:
                    st.warning("Na obrázku nebylo nalezeno žádné vozidlo IZS.")
                else:
                    st.markdown("### 📊 Nalezené objekty:")
                    for box in boxes:
                        class_id = int(box.cls[0])
                        class_name = model.names[class_id]
                        confidence = float(box.conf[0]) * 100
                        
                        st.write(f"- **{class_name.capitalize()}** (Jistota: {confidence:.1f} %)")