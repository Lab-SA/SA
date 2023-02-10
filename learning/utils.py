#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python version: 3.6

import copy
import torch
from torchvision import datasets, transforms
from .sampling import mnist_iid, mnist_noniid, mnist_noniid_unequal, mnist_iid_cluster

def get_mnist_train():
    data_dir = '../data/mnist/'
    apply_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    train_dataset = datasets.MNIST(data_dir, train=True, download=True, transform=apply_transform)
    return train_dataset

def get_mnist_test():
    data_dir = '../data/mnist/'
    apply_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    test_dataset = datasets.MNIST(data_dir, train=False, download=True, transform=apply_transform)
    return test_dataset

def get_users_data(args, num_users, train_dataset, isCluster=False, cluster=0, num_items=0):
    """ Returns a user group which is a dict where
    the keys are the user index and the values are the corresponding data for each of those users.
    """
    if args.dataset == 'mnist':
        # sample training data amongst users
        if args.iid:
            # Sample IID user data from Mnist
            if isCluster:
                user_groups = mnist_iid_cluster(train_dataset, num_users, cluster, num_items)
            else:
                user_groups = mnist_iid(train_dataset, num_users)
        else:
            # Sample Non-IID user data from Mnist
            if args.unequal:
                # Chose uneuqal splits for every user
                user_groups = mnist_noniid_unequal(train_dataset, num_users)
            else:
                # Chose euqal splits for every user
                user_groups = mnist_noniid(train_dataset, num_users)
    return user_groups

def average_weights(w, n):
    """
    Returns the average of the weights.
    """
    w_avg = copy.deepcopy(w)
    for key in w_avg.keys():
        w_avg[key] = torch.div(w_avg[key], n)
    return w_avg

def sum_weights(w):
    """
    Returns the sum of the weights.
    """
    w_sum = copy.deepcopy(w[0])
    for key in w_sum.keys():
        for i in range(1, len(w)):
            w_sum[key] += w[i][key]
    return w_sum

def add_to_weights(w, a):
    for param_tensor, value in w.items():
        w[param_tensor] = torch.add(value, a)
    return w

def average_weights_origin(w):
    """
    Returns the average of the weights.
    """
    w_avg = copy.deepcopy(w[0])
    for key in w_avg.keys():
        for i in range(1, len(w)):
            w_avg[key] += w[i][key]
        w_avg[key] = torch.div(w_avg[key], len(w))
    return w_avg

def exp_details(args):
    print('\nExperimental details:')
    print(f'    Model     : {args.model}')
    print(f'    Optimizer : {args.optimizer}')
    print(f'    Learning  : {args.lr}')
    print(f'    Global Rounds   : {args.epochs}\n')

    print('    Federated parameters:')
    if args.iid:
        print('    IID')
    else:
        print('    Non-IID')
    print(f'    Fraction of users  : {args.frac}')
    print(f'    Local Batch size   : {args.local_bs}')
    print(f'    Local Epochs       : {args.local_ep}\n')
    return