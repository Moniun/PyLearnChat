import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import random
import os
from hippo_model import HippoModel
from utils.config import HippoConfig
# 导入LLM客户端
from models.llm_client import LLMClient

# 设备配置
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------- 数据集（无需关键词，仅对话） --------------------------
class DialogueDataset(Dataset):
    def __init__(self, llm_client, hippo_config: HippoConfig, generation_prompt=None):
        self.data = []
        self.llm_client = llm_client
        self.max_seq_len = hippo_config.max_seq_len
        self.num_samples = hippo_config.num_samples
        self.data_path = hippo_config.data_path
        self.generation_prompt = generation_prompt
        
        if self.data_path and os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            print(f"生成{self.num_samples}个含长期记忆的对话...")
            self._generate_data()
            if self.data_path:
                with open(self.data_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _generate_data(self):
        """使用大语言模型生成含长期记忆的对话（跨轮次关联）"""
        # 使用大语言模型生成对话
        for _ in tqdm(range(self.num_samples), desc="使用大模型生成数据"):
            dialogue = self._generate_dialogue_with_llm()
            self.data.append(dialogue)
    
    def _generate_dialogue_with_llm(self):
        """使用大语言模型API调用生成符合要求的对话"""
        # 预定义的对话主题，如果没有提供自定义prompt
        default_topics = ["旅行计划", "项目开发", "学习安排", "健康管理", "工作会议"]
        topic = random.choice(default_topics)
        
        # 默认的生成prompt
        default_prompt = (
            f"请生成一段关于'{topic}'的对话，包含{random.randint(4, self.max_seq_len)}轮对话。\n"
            "对话应具有以下特点：\n"
            "1. 模拟用户和助手之间的自然交流\n"
            "2. 包含长期记忆特性，后续对话能引用前面提到的信息\n"
            "3. 每轮对话以'用户：'或'助手：'开头\n"
            "4. 内容连贯，符合逻辑\n"
            "5. 不要有多余的解释，只输出对话内容"
        )
        
        # 使用提供的prompt或默认prompt
        prompt = self.generation_prompt if self.generation_prompt else default_prompt
        
        try:
            # 使用大模型API生成对话（非流式）
            generated_text = self.llm_client.generate(prompt, stream=False)
            
            # 处理生成的对话，提取每行以'User:'或'Assistant:'开头的内容
            dialogue_lines = []
            for line in generated_text.split('\n'):
                line = line.strip()
                if line.startswith('User:') or line.startswith('Assistant:'):
                    dialogue_lines.append(line)
                    
                    # 确保对话长度在合理范围内
                    if len(dialogue_lines) >= self.max_seq_len:
                        break
            
            # 如果生成的对话不符合要求，返回一个备用的简单对话
            if len(dialogue_lines) < 4:
                return [f"User: 我们聊聊{topic}吧",
                        f"Assistant: 好的，关于{topic}你有什么具体问题吗？",
                        f"User: {topic}需要注意什么事项？",
                        f"Assistant: 关于{topic}，建议你提前做好计划"]
            
            return dialogue_lines
        except Exception as e:
            print(f"大模型API调用出错: {e}")
            # 出错时返回备用对话
            return [f"用户：我们聊聊{topic}吧",
                    f"助手：好的，关于{topic}你有什么具体问题吗？",
                    f"用户：{topic}需要注意什么事项？",
                    f"助手：关于{topic}，建议你提前做好计划"]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

# -------------------------- 向量理解器（生成对话摘要，替代关键词） --------------------------
class VectorInterpreter:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def interpret(self, vector):
        """用大模型API解析向量，生成对话摘要（体现时序关系）"""
        vector_str = ", ".join([f"{x:.3f}" for x in vector[:8]])
        prompt = (
            f"以下向量是一段对话的时序压缩表示：[{vector_str}]...\n"
            # f"对话片段：{dialogue_context[:2]}...\n"
            "请根据该向量还原这段对话，原对话格式为'User: 对话内容'或'Assistant: 对话内容'。"
        )
        
        try:
            # 使用大模型API生成摘要
            generated_summary = self.llm_client.generate(prompt, stream=False)
            return generated_summary.strip()
        except Exception as e:
            print(f"大模型API调用出错: {e}")
            # 出错时返回备用摘要
            return "这段对话主要讨论了用户关心的问题，助手提供了相关建议和信息。"

# -------------------------- 损失函数（对话语义重构损失） --------------------------
class DialogueSemanticLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2").to(device)
        self.mse_loss = nn.MSELoss()  # 语义向量重构损失

    def forward(self, generated_summary, original_dialogue):
        # 生成摘要的语义向量 VS 原始对话的语义向量
        summary_emb = self.embedder.encode(generated_summary, convert_to_tensor=True).to(device)
        dialogue_emb = self.embedder.encode("\n".join(original_dialogue), convert_to_tensor=True).to(device)
        
        # 最小化两者的语义差异
        return self.mse_loss(summary_emb, dialogue_emb)

# -------------------------- 训练主函数 --------------------------
def train(config, generation_prompt=None):
    """训练函数，使用大模型生成对话数据"""
    # 初始化LLM客户端
    llm_client = LLMClient(config.llm)

    # 初始化组件
    dataset = DialogueDataset(
        llm_client,
        config.hippo,
        generation_prompt=generation_prompt
    )
    dataloader = DataLoader(dataset, batch_size=config.hippo.batch_size, shuffle=True, collate_fn=lambda x: x)
    hippo_model = HippoModel(
        input_dim=config.hippo.input_dim,
        hidden_dim=config.hippo.hidden_dim,
        hippo_type=config.hippo.hippo_type,
        middle_dim=config.hippo.middle_dim,
        ffn_dim=config.hippo.ffn_dim,
        output_dim=config.hippo.output_dim,
        text_encoder_name=config.hippo.text_encoder_path
    ).to(device)
    interpreter = VectorInterpreter(llm_client)  # 生成对话摘要
    loss_fn = DialogueSemanticLoss()  # 基于语义的损失
    optimizer = optim.Adam(hippo_model.parameters(), lr=config.hippo.lr)

    # 训练循环
    for epoch in range(config.hippo.epochs):
        total_loss = 0.0
        hippo_model.train()
        
        for batch in tqdm(dataloader, desc=f"Epoch {epoch+1}/{config.hippo.epochs}"):
            optimizer.zero_grad()
            batch_loss = 0.0
            
            for item in batch:
                dialogue = item["dialogue"]
                
                # Hippo模型输出时序融合向量
                vec = hippo_model(dialogue)  # (output_dim,)
                
                # 大模型解析向量生成对话摘要
                generated_summary = interpreter.interpret(vec.detach().cpu().numpy())
                
                # 计算语义重构损失
                loss = loss_fn(generated_summary, dialogue)
                batch_loss += loss
            
            # 反向传播
            batch_loss /= len(batch)
            batch_loss.backward()
            optimizer.step()
            total_loss += batch_loss.item()
        
        print(f"Epoch {epoch+1} 平均损失: {total_loss/len(dataloader):.4f}")
        torch.save(hippo_model.state_dict(), config.hippo.save_path)

if __name__ == "__main__":
    # 示例1：使用大模型生成对话，使用默认prompt规则
    # train()
    
    # 加载配置
    from utils.config import load_config
    config = load_config()
    
    # 示例2：使用大模型并指定自定义prompt规则
    custom_prompt = (
        "请随机生成任意主题的用户与大模型之间的对话，包含2-10轮对话。\n"
        "格式要求：\n"
        "1. 每轮对话必须以'用户：'或'助手：'开头\n"
        "2. 对话内容要专业、实用，提供具体的信息或建议\n"
        "3. 不要包含任何对话内容以外的解释或说明"
    )
    train(config, generation_prompt=custom_prompt)
    
    # 示例3：使用其他配置（如有需要）
    # train(config)
