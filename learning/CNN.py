import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
mnist = input_data.read_data_sets("/tmp/data", one_hot = True)

def CNN(x):

    #mnist data를 받는 값
    input_layer = tf.reshape(x, [-1, 28, 28, 1])
 
    # 1st Convolution Layer
    # kernel size = 5 x 5, filter = 32, activation function = relu
    # 28 x 28 x 1 => 28 x 28 x 32
    kernel1 = tf.Variable(tf.truncated_normal(shape = [5, 5, 1, 32], stddev = 0.1))
    bias1 = tf.Variable(tf.constant(0.1, shape = [32]))
    conv1 = tf.nn.conv2d(input_layer, kernel1, strides = [1,1,1,1],
    padding = 'SAME') + bias1
    activation1 = tf.nn.relu(conv1)
 
    # 1st Pooling Layer
    # 28 x 28 x 32 => 14 x 14 x 32
    m_pool1 = tf.nn.max_pool(activation1, ksize = [1, 2, 2, 1], strides = [1, 2, 2, 1], 
    padding = 'SAME')
 
    # 2nd Convolution Layer
    # kernel Size = 5 x 5, filter = 64, activation function = relu
    # 14 x 14 x 32 => 14 x 14 x 64
    kernel2 = tf.Variable(tf.truncated_normal(shape = [5, 5, 32, 64], stddev = 0.1))
    bias2 = tf.Variable(tf.constant(0.1, shape = [64]))
    conv2 = tf.nn.conv2d(m_pool1, kernel2, strides = [1, 1, 1, 1], 
    padding = 'SAME') + bias2
    activation2 = tf.nn.relu(conv2)
    
    # 2nd Pooling Layer
    # 14 x 14 x 64 => 7 x 7 x 64
    m_pool2 = tf.nn.max_pool(activation2, ksize = [1, 2, 2, 1], strides = [1, 2, 2, 1],
    padding = 'SAME')
 
    # 7 x 7 x 64 => 1024
    kernel3 = tf.Variable(tf.truncated_normal(shape = [7*7*64, 1024], stddev = 0.1))
    bias3 = tf.Variable(tf.constant(0.1, shape = [1024]))
    flat1 = tf.reshape(m_pool2, [-1, 7*7*64])
    output1 = tf.matmul(flat1,kernel3) + bias3
    activation3 = tf.nn.relu(output1)
 
    # 1024 => 10
    kernel4 = tf.Variable(tf.truncated_normal(shape = [1024, 10], stddev = 0.1))
    bias4 = tf.Variable(tf.constant(0.1, shape = [10]))
    logit = tf.matmul(activation3, kernel4) + bias4
    y_predict = tf.nn.softmax(logit)
 
    return y_predict, logit

#Input,Output 받을 placeholder 정의
x = tf.placeholder(tf.float32, shape = [None, 784])
y = tf.placeholder(tf.float32, shape = [None, 10])
 
y_predict, logit = CNN(x)
 
Loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels = y, logits = logit))
step = tf.train.AdamOptimizer(0.005).minimize(Loss)
 
#정확도를 출력하기 위한 연산들 정의
correct_prediction = tf.equal(tf.argmax(y_predict, 1), tf.argmax(y, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


with tf.Session() as s:
    s.run(tf.global_variables_initializer())
 
    for i in range(0, 1000):
        #50개씩 MNIST 데이터를 불러온다.
        batch = mnist.train.next_batch(50)
 
        if i% 20 == 0:
            feed_dict={x: batch[0], y: batch[1]}
            train_accuracy = accuracy.eval(feed_dict)
            print('반복(Epoch): %d,  정확도: %f'%(i, train_accuracy))
 
        s.run([step], feed_dict={x: batch[0], y:batch[1]})
 
    #정확도 측정
    print(100.0 - accuracy.eval(feed_dict = {x: mnist.test.images, y:mnist.test.labels}))