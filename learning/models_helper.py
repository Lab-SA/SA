import torch
from iteration_utilities import deepflatten

def get_model_weights(model):
    return model.state_dict()

def weights_to_dic_of_list(weights):
    dic_weights = {}
    for param_tensor, value in weights.items():
        dic_weights[param_tensor] = value.tolist()
    return dic_weights

# list to tensor, dic
# returns new weights of model
def dic_of_list_to_weights(dic_weights):
    global args
    params = {}
    for param_tensor, value in dic_weights.items():
        if args.gpu: # cuda
            params[param_tensor] = torch.Tensor(value).cuda()
        else: # cpu
            params[param_tensor] = torch.Tensor(value).cpu()
    #model.load_state_dict(params)
    return params

def flatten_tensor(weights):
    """ flatten tensor weights into a one-dimensional list
    Args:
        weights (dict): model weights (model.state_dict())
    Returns:
        dict: weights shape information (key: layer name, value: shape)
        list: one-dimensional list
    """
    weights_info = {}
    flatten_weights = []
    for layer, item in weights.items():
        weights_info[layer] = item.shape
        flatten_weights = flatten_weights + list(deepflatten(item.tolist()))
    return weights_info, flatten_weights

def restore_weights_tensor(weights_info, flatten_weights):
    """ restore tensor weights from a one-dimensional list
    Args:
        weights_info (dict): weights shape information
        flatten_weights (list): one-dimensional list of original weights
    Returns:
        dict: model weights(tensor) (model.state_dict())
    """
    new_weights = {}
    prev = 0
    next = 0
    for layer, shape in weights_info.items():
        next = prev + shape.numel()
        layer_tensor = torch.Tensor(flatten_weights[prev:next]).reshape(shape)
        new_weights[layer] = layer_tensor
        prev = next
    return new_weights

def flatten_list(weights):
    """ flatten list of weights into a one-dimensional list
    Args:
        weights (dict): model weights (key: layer name, value: list (:NOT TENSOR))
    Returns:
        dict: weights shape information (key: layer name, value: shape)
        list: one-dimensional list
    """
    weights_info = {}
    flatten_weights = []
    for layer, item in weights.items():
        weights_info[layer] = torch.Tensor(item).shape
        flatten_weights = flatten_weights + list(deepflatten(item))
    return weights_info, flatten_weights

def restore_weights_list(weights_info, flatten_weights):
    """ restore list of weights from a one-dimensional list
    Args:
        weights_info (dict): weights shape information
        flatten_weights (list): one-dimensional list of original weights
    Returns:
        dict: model weights(tensor) (model.state_dict())
    """
    new_weights = {}
    prev = 0
    next = 0
    for layer, shape in weights_info.items():
        next = prev + shape.numel()
        layer_list = torch.Tensor(flatten_weights[prev:next]).reshape(shape).tolist()
        new_weights[layer] = layer_list
        prev = next
    return new_weights
