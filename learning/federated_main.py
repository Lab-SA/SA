import copy, time
import numpy as np

import torch

from .options import args_parser
from .update import LocalUpdate, test_inference
from .models import CNNMnist
from .utils import get_mnist_train, get_mnist_test, get_users_data, average_weights, exp_details


# 전역변수 선언
train_loss, train_accuracy, train_dataset = [], [], []
args = args_parser()
start_time = 0

# [호츌] : 서버, 클라이언트
# [리턴] : global_model 
# 처음 시작할 때만 호출도는 setup 함수.
def setup():
    global args, train_dataset
    # args = args_parser()
    # exp_details(args)

    if args.gpu:
        torch.cuda.set_device(int(args.gpu))
    device = 'cuda' if args.gpu else 'cpu'

    # BUILD MODEL
    if args.model == 'cnn':
        # Convolutional neural netork
        if args.dataset == 'mnist':
            global_model = CNNMnist(args=args)
    else:
        exit('Error: unrecognized model')

    # Set the model to train and send it to device.
    global_model.to(device)
    global_model.train()
    
    # get train data
    train_dataset = get_mnist_train()
    
    return global_model

# [호츌] : 서버
# [인자] : X
# [리턴] : user_groups[dict[int, Any]]
# user_groups: 각 유저가 가지는 데이터셋을 모아놓은 것
def get_user_dataset(num_users):
    global start_time, args, train_dataset, user_groups
    start_time = time.time()
    user_groups = get_users_data(args, num_users, train_dataset)
    return user_groups

# 서버는 user_groups[idx] 를 클라이언트로 전달
# ex) 0번 클라이언트에게 user_groups[0], 1번 클라이언트에게 user_groups[1] 전달

# [호츌] : 클라이언트
# [인자] : global_model, user_group(서버에게 받은 데이터셋), epoch(몇 번째 학습인지 저장해놓은 변수)
# [리턴] : local_model, local_weight, local_loss
# localupdate를 수행한 후 local_weight와 local_loss를 update하여 리턴
def local_update(global_model, user_group, epoch):
    global args, train_dataset
    global_model.train()
    local_model = LocalUpdate(args=args, dataset=train_dataset,
                                idxs=user_group)
    w, loss = local_model.update_weights(
        model=copy.deepcopy(global_model), global_round=epoch)
    local_weight = copy.deepcopy(w)
    local_loss = copy.deepcopy(loss)

    return local_model, local_weight, local_loss

# 클라언트는 local_model은 리턴받아 저장
# 서버로 local_weight, local_loss를 전달


# [호츌] : 서버
# [인자] : global_model, local_weight_sum (local_weight들의 합), local_losses (local_loss 들을 모은 배열) 
# [리턴] : global_model (업데이트된 global_model) 
# local train이 끝나고 서버는 해당 결과를 모아서 global_model을 업데이트 
def update_globalmodel(global_model, local_weight_sum):
    global train_loss

    #local weight의 합 평균 내기
    average_weight = average_weights(local_weight_sum)
    global_model.load_state_dict(average_weight) # update

    # loss
    # loss_avg = sum(local_losses) / len(local_losses)
    # train_loss.append(loss_avg)
    return global_model

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

# 서버는 전달받은 update된 global model을 클라이언트들에게 전송

# [호츌] : 클라이언트
# [인자] : local_model (바로 이전에 클라이언트가 학습한 결과), global_model (서버로부터 전달받은 update된 global_model) 
# [리턴] : acc (정확도)
# 매 epoch마다의 검증과 모든 학습 후 정확성 출력을 위해 새롭게 업데이트 된 global_model과 이전에 학습해서 나온 local_model을 비교
def test_accuracy(local_model, global_model):
    global_model.eval()
    acc, loss = local_model.inference(model=global_model)
    return acc

# 클라이언트는 리턴된 acc를 서버로 전달하고 local_train 시작

# [호츌] : 서버
# [인자] : list_acc (클라이언트들로부터 전달받은 acc들을 저장해놓은 배열), epoch(몇 번째 학습인지 저장해놓은 변수)
# [리턴] : X
# 클라이언트들이 보낸 acc 값들로 해당 학습의 정확도를 저장하고 epoch 매 2회마다 train loss 와 train accuracy를 출력
def add_accuracy(list_acc, epoch):
    # list_acc.append(acc)
    global train_accuracy
    train_accuracy.append(sum(list_acc)/len(list_acc))
    print_every = 2
    global train_loss
    if (epoch+1) % print_every == 0:
        print(f' \nAvg Training Stats after {epoch+1} global rounds:')
        print(f'Training Loss : {np.mean(np.array(train_loss))}')
        print('Train Accuracy: {:.2f}% \n'.format(100*train_accuracy[-1]))

# [호츌] : 서버
# [인자] : global_model
# [리턴] : X
# # 모든 학습이 끝난후 출력 
def test_model(global_model):
    global train_accuracy, args
    test_dataset = get_mnist_test()
    test_acc, test_loss = test_inference(args, global_model, test_dataset)
    
    #print(f' \n Results after {args.epochs} global rounds of training:')
    #print("|---- Avg Train Accuracy: {:.2f}%".format(100*train_accuracy[-1]))
    print("|---- Test Accuracy: {:.2f}%".format(100*test_acc))
    print("|---- Test Loss: {:.2f}%".format(100*test_loss))

    # Saving the objects train_loss and train_accuracy:
    # file_name = '../save/objects/{}_{}_{}_C[{}]_iid[{}]_E[{}]_B[{}].pkl'.\
    #     format(args.dataset, args.model, args.epochs, args.frac, args.iid,
    #            args.local_ep, args.local_bs)

    # with open(file_name, 'wb') as f:
    #     pickle.dump([train_loss, train_accuracy], f)
    global start_time
    print('\n Total Run Time: {0:0.4f}'.format(time.time()-start_time))
