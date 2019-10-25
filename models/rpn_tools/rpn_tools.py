# -*- coding: utf-8 -*-
'''
# @Author  : syshen
# @date    : 2019/1/16 18:19
# @File    : region regression
'''
from __future__ import absolute_import
import torch
import torch.nn as nn
import torch.nn.functional as F

from .proposal_layer import ProposalLayer
from .anchor_target_layer import AnchorTargetLayer
from models.smoothl1loss import _smooth_l1_loss

from ..backbone.basic_modules import kaiming_init, normal_init
from .anchor_tools import Anchor


class RPNLoss(nn.Module):
    def __init__(
            self, num_anchors, rpn_batch, neg_overlap, pos_overlap, pos_weight, fraction, inside_weight,
            clobber_pos):
        super(RPNLoss,self).__init__()
        self.num_anchors = num_anchors
        self.get_targets = AnchorTargetLayer(rpn_batch, neg_overlap, pos_overlap, pos_weight, fraction,
                                             inside_weight, clobber_pos)

    def forward(self, scores, bboxes_pred, anchors, im_info, gt_boxes, loss_type="smoothL1loss"):
        batch_size, _, h, w = scores.size()
        with torch.no_grad():
            rpn_label, bbox_targets, inside_weights, outside_weights = \
                self.get_targets(scores.detach(), anchors, self.num_anchors, im_info, gt_boxes)

        # compute classification loss
        #scores = scores.reshape(batch_size, 2, -1, w)
        scores = scores.permute(0, 2, 3, 1).reshape(batch_size, -1, 2)
        rpn_label = rpn_label.reshape(batch_size, -1)
        rpn_keep = rpn_label.reshape(-1).ne(-1).nonzero().reshape(-1)
        scores = torch.index_select(scores.reshape(-1, 2), 0, rpn_keep)
        rpn_label = torch.index_select(rpn_label.reshape(-1), 0, rpn_keep.data).long()

        fg_cnt = torch.sum(rpn_label.data.ne(0))

        rpn_loss_cls = F.cross_entropy(scores, rpn_label)

        bboxes_pred = bboxes_pred.permute(0, 2, 3, 1).reshape(batch_size, -1, 4)
        rpn_loss_box = _smooth_l1_loss(bboxes_pred, bbox_targets, inside_weights, outside_weights, sigma=3, dim=[1, 2])

        return rpn_loss_cls, rpn_loss_box

class RPNSingleModule(nn.Module):

    """ region proposal network """

    def __init__(self, cfg):
        super(RPNSingleModule, self).__init__()

        self.inchannels = cfg.inchannels  # get depth of input feature map, e.g., 512
        self.output_channels = cfg.output_channels  # get depth of input feature map, e.g., 512
        self.anchor_scales = cfg.scales
        self.anchor_ratios = cfg.ratios
        self.feat_stride = cfg.stride

        # proposal layer
        self.pre_nms = cfg.pre_nms
        self.post_nms = cfg.post_nms
        # self.nms_thresh = cfg.model.rpn.nms_thresh

        rpn_batch = cfg.batch_size
        negative_overlap = cfg.neg_thresh
        positive_overlap = cfg.pos_thresh
        positive_weight = cfg.pos_weight
        fraction = cfg.fraction
        inside_weight = cfg.inside_weight
        clobber_positive = cfg.clobber_positive
        self.nms_thresh = cfg.nms_thresh

        # define the convrelu layers processing input feature map
        self.rpn_preconv = nn.Conv2d(self.inchannels, self.output_channels, 3, 1, 1, bias=True)

        # define bg/fg classifcation score layer
        # 2(bg/fg) * 9 (anchors)
        self.num_anchors = len(self.anchor_scales) * len(self.anchor_ratios)
        self.nc_score_out = self.num_anchors * 2
        self.cls_pred = nn.Conv2d( self.output_channels, self.nc_score_out, 1, 1, 0)

        # define anchor box offset prediction layer
        # 4(coords) * 9 (anchors)
        self.nc_bbox_out = self.nc_score_out * 2
        self.bbox_pred = nn.Conv2d(self.output_channels, self.nc_bbox_out, 1, 1, 0)

        # define anchor genarator layer
        self.anchor = Anchor(self.feat_stride, self.anchor_ratios, self.anchor_scales)

        # define proposal layer
        self.proposals = ProposalLayer( self.feat_stride, nms_thresh=self.nms_thresh, min_size=self.feat_stride)

        self.rpn_loss = RPNLoss(self.num_anchors, cfg.batch_size, cfg.neg_thresh, cfg.pos_thresh, cfg.pos_weight, cfg.fraction, cfg.inside_weight, cfg.clobber_positive)

    def __init_weights__(self):
        kaiming_init(self.cls_pred)
        kaiming_init(self.bbox_pred)

    def forward(self, base_feat, im_info, gt_boxes):

        batch_size, _ , feat_height, feat_width = base_feat.size()

        # return feature map after convrelu layer
        rpn_conv1 = F.relu(self.rpn_preconv(base_feat), inplace=True)
        # get rpn classification score
        scores = self.cls_pred(rpn_conv1)

        # get rpn offsets to the anchor boxes
        bboxes_pred = self.bbox_pred(rpn_conv1)

        anchors = self.anchor.grid_anchors([feat_height, feat_width], self.feat_stride, base_feat.device)

        rois = self.proposals(scores.detach(), bboxes_pred.detach(), anchors, self.num_anchors, im_info, self.pre_nms, self.post_nms, self.nms_thresh)

        # generating training labels and build the rpn loss
        rpn_loss_cls = rpn_loss_box = 0.0

        if self.training:
            assert gt_boxes is not None

            rpn_loss_cls, rpn_loss_box = self.rpn_loss(scores, bboxes_pred, anchors.detach(), im_info, gt_boxes)

            return rois, rpn_loss_cls, rpn_loss_box
        else:
            return rois


def get_model(config):
    return RPNSingleModule(config)