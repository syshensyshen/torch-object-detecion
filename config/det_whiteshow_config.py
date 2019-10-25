gpus=['0', ]
dataset="xml"
train_path="/data/ssy/outwrad-1024/train"
val_path=None
save_dir="save_models/"
resume_model=''
model_name='outward_'
lr=0.01
epochs=100
batch_size_per_gpu=3
num_works=3
class_list=(['other', 'scratch_deep', 'scratch_shallow', 'fracture'])
defect_class_list=(['hook', 'slide block', 'together'])
rename_class_list={},
confidence_per_cls={'hook': [0.1], 'slide block': [0.1], 'together': [0.98]}
save_model_interval=10
models = dict(
    structs = {'backbone': 'resnet', 'featurescompose': 'hypernet', 'rpn_tools': 'rpn_tools', 'rcnn_tools': 'rcnn_tools'},
    backbone=dict(
        depth=50,
        pretrained=False,
    ),
    featurescompose=dict(
        hyper_dim=0,
        inchannels=[256, 512, 1024, 2048],
        # inchannels=[48, 96, 192, 256],
        output_channels=256,
    ),
    rpn_tools=dict(
        stride=4,
        scales=[1.2, 4, 8, 16, 32, 64, 128],
        ratios=[0.0025, 0.05, 0.125, 0.28, 1.0, 3.5, 8.0, 20, 40],
        inchannels=256,
        output_channels = 256,
        pos_thresh=0.7,
        neg_thresh=0.3,
        # min_pos_iou=0.5,
        fraction = 0.25,
        # total number of examples
        batch_size = 256,
        # nms threshold used on rpn proposals
        nms_thresh = 0.7,
        # number of top scoring boxes to keep before apply nms to rpn proposals
        pre_nms = 12000,
        # number of top scoring boxes to keep after applying nms to rpn proposals
        post_nms = 6000,
        # proposal height and width both need to be greater than rpn_min_size (at orig image scale)
        min_size = 4,
        # deprecated (outside weights)
        inside_weight = 1.0,
        clobber_positive=False,
        # give the positive rpn examples weight of p * 1 / {num positives}
        # and give negatives a weight of (1 - p)
        # set to -1.0 to use uniform example weighting
        pos_weight = -1.0,
    ),
    rcnn_tools=dict(
        ohem_rcnn=False,
        class_list=class_list,
        stride = 4,
        inchannels = 256,
        pooling_size = 7,
        rcnn_first = 512,
        rcnn_last_din = 768,
        mode = 'align',
        mean = [0,0,0,0],
        std = [0.1,0.1,0.2,0.2],
        inside_weight = [1.0,1.0,1.0,1.0],
        fraction = 0.25,
        batch_size = 128,
        fg_thresh = 0.5,
        bg_thresh_hi = 0.5,
        bg_thresh_lo = 0.5,
        with_avg_pool = False,
        class_agnostic = False,
    )
)
