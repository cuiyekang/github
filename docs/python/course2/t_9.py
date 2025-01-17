import numpy as np
#pip3 install pillow
from PIL import Image,ImageDraw,ImageFont
#pip3 install scikit-image
from skimage import transform as tf

def create_captcha(text,shear = 0,size = (100,24)):
    im= Image.new("L",size,"black")
    draw = ImageDraw.Draw(im)
    font=ImageFont.truetype(r"arial.ttf", 20)
    for i in range(len(text)):
        draw.text((2 +i*20,2),text[i],fill=1,font=font)
    #draw.text((2,2),text,fill=1,font=font)
    image=np.array(im)
    affine_tf = tf.AffineTransform(shear = shear)
    image= tf.warp(image,affine_tf)
    return image / image.max()

from matplotlib import pyplot as plt

# image = create_captcha("GENE",shear=0.5)

# plt.imshow(image,cmap="gray")
# plt.show()

from skimage.measure import label,regionprops

def segment_image(image):
    labeled_image = label(image>0)
    subimages =[]
    for region in regionprops(labeled_image):
        start_x,start_y,end_x,end_y = region.bbox
        subimages.append(image[start_x:end_x,start_y:end_y])
    if len(subimages) == 0:
        return [image,]
    else:
        return subimages

# subimages = segment_image(image)

# f,axes = plt.subplots(1,len(subimages),figsize=(10,3),squeeze = True)

# print(axes)

# for i in range(len(subimages)):
#     axes[i].imshow(subimages[i],cmap="gray")

# plt.show()

from sklearn.utils import check_random_state

random_state = check_random_state(14)
letters = list("ACBDEFGHIJKLMNOPQRSTUVWXYZ")
shear_values = np.arange(0,0.5,0.05)

def generate_sample(random_state=None):
    random_state = check_random_state(random_state)
    letter = random_state.choice(letters)
    shear = random_state.choice(shear_values)
    return create_captcha(letter,shear = shear,size = (20,20)),letters.index(letter)

# image ,target = generate_sample(random_state)
# plt.imshow(image,cmap="gray")
# print("The target for this image is: {0}".format(target))

dataset,targets = zip(*(generate_sample(random_state) for i in range(30)))
dataset = np.array(dataset,dtype='float')
targets = np.array(targets)

# 20*20的矩阵
# print(dataset[0])

from sklearn.preprocessing import OneHotEncoder
onehot = OneHotEncoder()
y = onehot.fit_transform(targets.reshape(targets.shape[0],1))
#转密集矩阵
y = y.todense()

from skimage.transform import resize

dataset = np.array([resize(segment_image(sample)[0],(20,20)) for sample in dataset])
x = dataset.reshape((dataset.shape[0],dataset.shape[1]*dataset.shape[2]))

from sklearn.model_selection import train_test_split

x_train,x_test,y_train,y_test = train_test_split(x,y,train_size=0.9)

#需要下载github 的安装包 https://github.com/pybrain/pybrain
#下载后解压到某文件夹下，cmd到此文件夹下执行 python setup.py install
from pybrain.datasets import SupervisedDataSet

# print(x.shape)
# print(y.shape)

training = SupervisedDataSet(x.shape[1],y.shape[1])
for i in range(x_train.shape[0]):
    training.addSample(x_train[i],y_train[i])

testing = SupervisedDataSet(x.shape[1],y.shape[1])
for i in range(x_test.shape[0]):
    testing.addSample(x_test[i],y_test[i])

from pybrain.tools.shortcuts import buildNetwork
net = buildNetwork(x.shape[1],100,y.shape[1],bias = True)

from pybrain.supervised.trainers import BackpropTrainer
trainer = BackpropTrainer(net,training,learningrate = 0.01,weightdecay = 0.01)

trainer.trainEpochs(epochs = 20)
predictions = trainer.testOnClassData(dataset = testing)

from sklearn.metrics import f1_score

f1 = f1_score(predictions,y_test.argmax(axis=1),average = 'micro')

print("F-score: {0:.2f}".format(f1))


from sklearn.metrics import classification_report

#print(classification_report(y_test.argmax(axis=1),predictions))

def predict_captcha(captcha_image,neural_network):
    subimages = segment_image(captcha_image)
    predicted_word =""
    for subimage in subimages:
        subimage = resize(subimage,(20,20))
        outputs = net.activate(subimage.flatten())
        prediction = np.argmax(outputs)
        predicted_word += letters[prediction]
    return predicted_word

# word = "GENE"
# captcha = create_captcha(word,shear=0.2)

# # plt.imshow(captcha,cmap="gray")
# # plt.show()


# print(predict_captcha(captcha,net))

def test_prediction(word,net,shear=0.2):
    captcha = create_captcha(word,shear=shear)
    prediction = predict_captcha(captcha,net)
    prediction = prediction[:4]
    return word==prediction,word,prediction

from nltk.corpus import words

valid_words = [word.upper() for word in words.words() if len(word)==4]
valid_words = valid_words[:100]
# num_correct = 0
# num_incorrect = 0

# for word in valid_words:
#     correct,word,prediction = test_prediction(word,net,shear = 0.2)
#     if correct:
#         num_correct +=1
#     else:
#         num_incorrect +=1

# print("Number correct is {0}".format(num_correct))
# print("Number incorrect is {0}".format(num_incorrect))

from sklearn.metrics import confusion_matrix
cm = confusion_matrix(np.argmax(y_test,axis=1),predictions)

# plt.figure(figsize=(20,20))
# plt.imshow(cm,cmap="Blues")
# plt.show()

from nltk.metrics import edit_distance
steps = edit_distance("STEP","STOP")
print("The number of steps needed is: {0}".format(steps))

def compute_distance(prediction,word):
    return len(prediction)-sum(prediction[i]==word[i] for i in range(len(prediction)))

from operator import itemgetter

def improved_prediction(word,net,dictionary,shear=0.2):
    captcha = create_captcha(word,shear=shear)
    prediction = predict_captcha(captcha,net)
    prediction = prediction[:4]
    if prediction not in dictionary:
        distances = sorted([(word,compute_distance(prediction,word)) for word in dictionary],key = itemgetter(1))
        best_word = distances[0]
        prediction  = best_word[0]
    return word == prediction,word,prediction

num_correct = 0
num_incorrect = 0

for word in valid_words:
    correct,word,prediction = improved_prediction(word,net,valid_words,shear=0.2)
    if correct:
        num_correct +=1
    else:
        num_incorrect +=1

print("Number correct is {0}".format(num_correct))
print("Number incorrect is {0}".format(num_incorrect))






