#!/usr/bin/env python
#-*- encoding: utf8 -*-

import json
import random

import rospy
import actionlib

from mhri_msgs.msg import RenderSceneAction, RenderSceneFeedback, RenderSceneResult
from mhri_msgs.msg import RenderItemAction, RenderItemFeedback, RenderItemResult
from mhri_msgs.srv import GetInstalledGestures


class MotionRenderer:
    is_rendering = {}
    render_client = {}
    cb_start = {}
    #cb_rendering = {}
    cb_done = {}

    def __init__(self):
        self.render_client['say'] = actionlib.SimpleActionClient('render_speech', RenderItemAction)
        self.render_client['say'].wait_for_server()
        #
        self.render_client['sm'] = actionlib.SimpleActionClient('render_gesture', RenderItemAction)
        self.render_client['sm'].wait_for_server()

        try:
            rospy.wait_for_service('get_installed_gestures', timeout=1)
        except rospy.exceptions.ROSException as e:
            rospy.logerr(e)
            quit()

        self.get_motion = rospy.ServiceProxy('get_installed_gestures', GetInstalledGestures)
        json_data = self.get_motion()
        self.motion_tag = json.loads(json_data.gestures)

        rospy.loginfo('[%s] Success to get motion_tag from gesture server' % rospy.get_name())


        self.render_client['expression'] = actionlib.SimpleActionClient('render_facial_expression', RenderItemAction)
        self.render_client['expression'].wait_for_server()

        self.render_client['sound'] = actionlib.SimpleActionClient('render_sound', RenderItemAction)
        self.render_client['sound'].wait_for_server()

        self.server = actionlib.SimpleActionServer('render_scene', RenderSceneAction, self.execute_callback, False)
        self.server.register_preempt_callback(self.preempt_callback)
        self.server.start()

        # Status flags
        self.is_rendering['say'] = False
        self.is_rendering['sm'] = False
        self.is_rendering['expression'] = False
        self.is_rendering['sound'] = False

        # Register callback functions.
        self.cb_start['say'] = self.handle_render_say_start
        #self.cb_rendering['say'] = self.handle_render_say_rendering
        self.cb_done['say'] = self.handle_render_say_done

        self.cb_start['sm'] = self.handle_render_sm_start
        #self.cb_rendering['sm'] = self.handle_render_sm_rendering
        self.cb_done['sm'] = self.handle_render_sm_done

        self.cb_start['expression'] = self.handle_render_expression_start
        #self.cb_rendering['expression'] = self.handle_render_expression_rendering
        self.cb_done['expression'] = self.handle_render_expression_done

        self.cb_start['sound'] = self.handle_render_sound_start
        #self.cb_rendering['sound'] = self.handle_render_sound_rendering
        self.cb_done['sound'] = self.handle_render_sound_done

        rospy.loginfo("[%s] Initialized." % rospy.get_name())


    def handle_render_say_done(self, state, result):
        self.is_rendering['say'] = False

    def handle_render_say_start(self):
        self.is_rendering['say'] = True
        pass


    def handle_render_sm_done(self, state, result):
        self.is_rendering['sm'] = False

    def handle_render_sm_start(self):
        self.is_rendering['sm'] = True


    def handle_render_expression_done(self, state, result):
        self.is_rendering['expression'] = False

    def handle_render_expression_start(self):
        self.is_rendering['expression'] = True


    def handle_render_sound_done(self, state, result):
        self.is_rendering['sound'] = False

    def handle_render_sound_start(self):
        self.is_rendering['sound'] = True



    '''
	Server
	'''

    def preempt_callback(self):
        rospy.logwarn('Motion Rendering Preempted.')
        if self.is_speaking_now:
            self.speech_client.cancel_all_goals()
        if self.is_playing_now:
            self.gesture_client.cancel_all_goals()

    def execute_callback(self, goal):
        # Do lots of awesome groundbreaking robot stuff here
        rospy.logwarn('Motion Rendering Started.')
        result = RenderSceneResult()

        render_scene = json.loads(goal.render_scene)
        render_scene_time = {}
        for k, v in render_scene.items():
            if v != {} and k != 'emotion':
                render_scene_time[k] = v['offset']

        # Sort by delay time
        scene_item_sorted_by_time = sorted(render_scene_time, key=render_scene_time.get)
        first_offset_time = render_scene[scene_item_sorted_by_time[0]]['offset']
        rospy.sleep(first_offset_time)

        print render_scene

        for i in range(0, len(scene_item_sorted_by_time) - 1):

            print 'send_action_goal:' + scene_item_sorted_by_time[i]
            delta_time = render_scene[scene_item_sorted_by_time[i+1]]['offset'] - render_scene[scene_item_sorted_by_time[i]]['offset']
            print 'sleep: %f'%delta_time
            rospy.sleep(delta_time)

        print 'send_action_goal:' + scene_item_sorted_by_time[-1]



        '''
		if goal.emotion == 'neutral':
			self.pub_face_emotion.publish(
			    SetFacialExpression.NEUTRAL, goal.emotion_intensity)
		elif goal.emotion == 'happiness':
			self.pub_face_emotion.publish(
			    SetFacialExpression.HAPPINESS, goal.emotion_intensity)
		elif goal.emotion == 'surprise':
			self.pub_face_emotion.publish(
			    SetFacialExpression.HAPPINESS, goal.emotion_intensity)
		elif goal.emotion == 'anger':
			self.pub_face_emotion.publish(
			    SetFacialExpression.HAPPINESS, goal.emotion_intensity)
		elif goal.emotion == 'sadness':
			self.pub_face_emotion.publish(
			    SetFacialExpression.HAPPINESS, goal.emotion_intensity)
		elif goal.emotion == 'disgust':
			self.pub_face_emotion.publish(
			    SetFacialExpression.HAPPINESS, goal.emotion_intensity)
		elif goal.emotion == 'fear':
			self.pub_face_emotion.publish(
			    SetFacialExpression.HAPPINESS, goal.emotion_intensity)

		if goal.gesture != '':
			# When robot requested play gesture, the idle motion is disabled temporary
			self.is_playing_now = True

			# print goal.gesture
			recv_data = goal.gesture.split(':')
			if recv_data[0] == 'sm':
				# print recv_data
				if recv_data[1] in self.motion_tag:
					gesture_name = self.motion_tag[recv_data[1]][
					    random.randrange(0, len(self.motion_tag[recv_data[1]]))]
				else:
					gesture_name = recv_data[1]
			elif recv_data[0] == 'pm':
				gesture_name = recv_data[1]

			gesture_goal = GestureActionGoal(gesture=gesture_name)
			self.gesture_client.send_goal(goal=gesture_goal, done_cb=self.gesture_done_cb,
			                              feedback_cb=self.gesture_playing_cb, active_cb=self.gesture_start_cb)

		# rospy.sleep(2)

		if goal.say != '':
			# When robot is speaking, the speech_recognition is disabled temporary
			self.is_speaking_now = True
			self.is_gesture_only = False
			speech_goal = SpeechActionGoal(say=goal.say)
			self.speech_client.send_goal(goal=speech_goal, done_cb=self.speech_done_cb,
			                             feedback_cb=self.speech_speaking_cb, active_cb=self.speech_start_cb)
		else:
			# Gesture Only
			self.is_gesture_only = True

		while self.is_speaking_now or self.is_playing_now:
			# rospy.logwarn('%d %d'%(self.is_speaking_now, self.is_playing_now))

			if self.is_gesture_only:
				rospy.sleep(0.2)
				continue

			if not self.is_speaking_now and self.is_playing_now:
				self.sync_count_gesture += 1
				if self.sync_count_gesture > 3:
					self.gesture_client.cancel_all_goals()
					self.sync_count_gesture = 0

			rospy.sleep(0.2)

		self.pub_face_emotion.publish(SetFacialExpression.PREVIOUS_FACE, 1.0)
        '''
        rospy.logwarn('Motion Rendering Completed.')

        result.result = True
        self.server.set_succeeded(result)


if __name__ == '__main__':
    rospy.init_node('motion_renderer', anonymous=False)
    m = MotionRenderer()
    rospy.spin()
