import torch
import torch.nn as nn

from transformers.models.bert.modeling_bert import BertConfig, BertEncoder, BertModel


class LSTMwithAttn(nn.Module):
    
    def __init__(self, input_dim, hidden_dim, output_dim, num_layers, num_heads=8, dropout=0.1, device='cpu'):
        super(LSTMwithAttn, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.output_dim = output_dim
        self.dropout = dropout
        self.device = device
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        
        self.config = BertConfig(
            hidden_size=hidden_dim,
            num_hidden_layers=num_layers,
            num_attention_heads=num_heads,
            intermediate_size=hidden_dim,
            hidden_dropout_prob=dropout,
            attention_probs_dropout_prob=dropout,
        )
        self.encoder = BertEncoder(self.config)   
        
        self.act = nn.SiLU()
        self.fc = nn.Linear(hidden_dim, output_dim)
        
        self.init_weights()
        
        
    def init_hidden_state(self, batch_size):
        h0 = torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(self.device)
        c0 = torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(self.device)
        return (h0, c0)
    
    
    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
                    
    
    def generate_attn_mask(self, x):
        seq_len = x.size(1)
        attn_mask = torch.tril(torch.ones((seq_len, seq_len))).view(1, seq_len, seq_len).to(self.device)
        
        return attn_mask
        
        
    def forward(self, x):
        batch_size = x.size(0)
        
        h0, c0 = self.init_hidden_state(batch_size)
        
        output, (hidden, cell) = self.lstm(x, (h0, c0))
        
        output = output.contiguous().view(batch_size, -1, self.hidden_dim)
        
        # Attention Mask
        attn_mask = self.generate_attn_mask(x)
        extended_attn_mask = attn_mask[None, :, :, :].expand(batch_size, -1, -1, -1)
        extended_attn_mask = (1.0 - extended_attn_mask) * -10000.0
        
        encoder_outputs = self.encoder(output, attention_mask=extended_attn_mask)
        
        output = self.act(encoder_outputs.last_hidden_state)
        output = self.fc(output)
        
        return output