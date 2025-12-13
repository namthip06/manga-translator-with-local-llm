import ollama

# หากคุณสร้าง Client โดยระบุ Host/Port
client = ollama.Client(host='http://localhost:11434')
list_response = client.list()

# คุณสามารถเข้าถึง URL ที่ Client กำลังพยายามเชื่อมต่อ
# print(f"Ollama models: {models}")
# output
# models=[Model(model='qwen2.5-coder:7b', modified_at=datetime.datetime(2025, 12, 6, 15, 47, 12, 668311, tzinfo=TzInfo(25200)), digest='dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364', size=4683087561, details=ModelDetails(parent_model='', format='gguf', family='qwen2', families=['qwen2'], parameter_size='7.6B', quantization_level='Q4_K_M')), Model(model='scb10x/typhoon-translate-4b:latest', modified_at=datetime.datetime(2025, 12, 1, 13, 26, 3, 499730, tzinfo=TzInfo(25200)), digest='1be00963c2b30eaf63d7c26befb39c59f8adda5e3deca7bf07d1e2e7995ac09e', size=2489894494, details=ModelDetails(parent_model='', format='gguf', family='gemma3', families=['gemma3'], parameter_size='3.9B', quantization_level='Q4_K_M')), Model(model='llama3.2:latest', modified_at=datetime.datetime(2025, 11, 18, 23, 39, 50, 452165, tzinfo=TzInfo(25200)), digest='a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72', size=2019393189, details=ModelDetails(parent_model='', format='gguf', family='llama', families=['llama'], parameter_size='3.2B', quantization_level='Q4_K_M'))]

try:
    models_list = list_response.get('models', []) 
except Exception as e:
    print(f"Error listing models: {e}")

try:
    print(len(models_list))
    for model in models_list:
        print(model.get('model'))
except Exception as e:
    print(f"Error listing models: {e}")

# print(f"📦 พบโมเดลทั้งหมด: {len(models_list)} รายการ")
# print("-" * 50)
# print(f"{'ชื่อโมเดล':<35} | {'ขนาด (GB)':<10} | {'ID (Digest)':<15}")
# print("-" * 50)

# for model_info in models_list:
#     name = model_info.get('name', 'N/A')
#     size_bytes = model_info.get('size', 0)
#     digest = model_info.get('digest', 'N/A')
    
#     size_gb = size_bytes / (1024**3)
    
#     print(f"{name:<35} | {size_gb:^10.2f} | {digest:<15}")
    
# print("-" * 50)