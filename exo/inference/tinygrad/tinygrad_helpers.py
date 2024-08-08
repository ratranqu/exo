from tinygrad.nn.state import safe_load, torch_load
from tinygrad import Tensor
from pathlib import Path
import json
from typing import List
from exo.inference.shard import Shard
from exo.helpers import DEBUG

# **** helper functions ****
def concat_weights(models, device=None):
  def convert(name) -> Tensor:
    disk_tensors: List[Tensor] = [model[name] for model in models]
    if len(disk_tensors) == 1 or len(disk_tensors[0].shape) == 1:
      return disk_tensors[0].to(device=device)
    axis = 1 if name.endswith(".attention.wo.weight") or name.endswith(".feed_forward.w2.weight") else 0
    lazy_tensors = [data.to(device=device) for data in disk_tensors]
    return lazy_tensors[0].cat(*lazy_tensors[1:], dim=axis)
  return {name: convert(name) for name in {name: None for model in models for name in model}}

def load(fn:str, shard: Shard):
  if fn.endswith('.index.json'):
    with open(fn) as fp: weight_map = json.load(fp)['weight_map']
    parts = {}
    filtered_weight_map = {}
    for k, n in weight_map.items():
      if k.startswith("model.layers."):
        layer_num = int(k.split('.')[2])
        if layer_num < shard.start_layer or layer_num > shard.end_layer:
          continue

      parts[n] = load(str(Path(fn).parent / Path(n).name), shard)
      filtered_weight_map[k] = n
    if DEBUG >= 2: print(f"Excluded model param keys for {shard=}: {set(weight_map.keys()) - set(filtered_weight_map.keys())}")
    return {k: parts[n][k] for k, n in filtered_weight_map.items()}
  elif fn.endswith(".safetensors"):
    return safe_load(fn)
  else:
    return torch_load(fn)
