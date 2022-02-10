import os
import copy
import time
import pickle
import numpy as np
from tqdm import tqdm

import torch

from options import args_parser
from update import LocalUpdate, test_inference
from models import CNNMnist
from utils import get_dataset, average_weights, exp_details

# [호츌] : 서버
# [인자] : global_weigth (평균된 local weight), local_losses (local_loss 들을 모은 배열) 
# [리턴] : global_model 
# local train이 끝나고 서버는 해당 결과를 모아서 global_model을 업데이트 
def update_globalmodel(global_weight, local_losses):
    global_model.load_state_dict(global_weight)
    loss_avg = sum(local_losses) / len(local_losses)
    train_loss.append(loss_avg)
    return global_model

# 서버는 전달받은 update된 global model과 서버에서 계산한 global_weights를 클라이언트들에게 전송

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
# [인자] : list_acc (클라이언트들로부터 전달받은 acc들을 저장해놓은 배열) 
# [리턴] : X
# 클라이언트들이 보낸 acc 값들로 해당 학습의 정확도를 저장하고 epoch 매 2회마다 train loss 와 train accuracy를 출력
def add_accuracy(list_acc):
    # list_acc.append(acc)
    train_accuracy.append(sum(list_acc)/len(list_acc))
    if (epoch+1) % print_every == 0:
        print(f' \nAvg Training Stats after {epoch+1} global rounds:')
        print(f'Training Loss : {np.mean(np.array(train_loss))}')
        print('Train Accuracy: {:.2f}% \n'.format(100*train_accuracy[-1]))

# [호츌] : 서버
# [인자] : global_model (최종 학습이 끝난 후의 global_model) 
# [리턴] : X
# 클라이언트들이 보낸 acc 값들로 해당 학습의 정확도를 저장하고 epoch 매 2회마다 train loss 와 train accuracy를 출력
# 모든 학습이 끝난후 출력 
# 서버가 함수 호출 (global_model을 인자로 보내야 함)
def test_result(global_model):
    test_acc, test_loss = test_inference(args, global_model, test_dataset)

    print(f' \n Results after {args.epochs} global rounds of training:')
    print("|---- Avg Train Accuracy: {:.2f}%".format(100*train_accuracy[-1]))
    print("|---- Test Accuracy: {:.2f}%".format(100*test_acc))

    # Saving the objects train_loss and train_accuracy:
    file_name = '../save/objects/{}_{}_{}_C[{}]_iid[{}]_E[{}]_B[{}].pkl'.\
        format(args.dataset, args.model, args.epochs, args.frac, args.iid,
               args.local_ep, args.local_bs)

    with open(file_name, 'wb') as f:
        pickle.dump([train_loss, train_accuracy], f)

    print('\n Total Run Time: {0:0.4f}'.format(time.time()-start_time))

