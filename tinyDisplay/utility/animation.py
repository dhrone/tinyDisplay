# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Animation utility for tinyDisplay - provides thread-based animation capability.
"""

import logging
import time
from queue import Empty, Full, Queue
from threading import Event, Thread

from simple_pid import PID

from tinyDisplay.exceptions import NoResult

class animate(Thread):
    """
    Animate function.

    Create a thread to call a function at a specified number of calls per second (CPS)
    placing the results in a queue for consumption

    :param function: the function (or method) that will be called
    :type function: function or method
    :param cps: Calls per second.  The rate to call the provided function
    :type cps: int
    :param queueSize: The size of the queue used to record return results from function
    :type queueSize: int
    :param args:  The arguments to pass to the function
    :type args: tuple
    :param kwargs:  The keyworded arguments to pass to the function
    :type kwargs: dict

    To begin animation, call the start method.  Example::
        a = animate(function=func, cps=10)
        a.start

    ..note:
        The animate function uses a queue to pass results back.  This allows for the
        results to be consumed asynchronous.  If the queue fills up though,
        the function will no longer be called until space opens up in the queue.
    """

    def __init__(self, function=None, cps=1, queueSize=100, *args, **kwargs):
        Thread.__init__(self)
        assert function, "You must supply a function to animate"
        self._speed = cps

        Kp = 5
        Ki = 0.2
        Kd = 0.05
        self._pid = PID(
            Kp,
            Ki,
            Kd,
            setpoint=self._speed,
            sample_time=0.1,
            output_limits=(cps * 0.1, None),
        )

        self._function = function
        self._args = args
        self._kwargs = kwargs

        self.fps = 0
        self._running = True
        self._queue = Queue(maxsize=queueSize)
        self._event = Event()
        self._forceEvent = Event()

    @property
    def empty(self):
        """
        Return whether queue is empty.

        :returns: True of empty, False if not
        """
        return self._queue.empty()

    @property
    def full(self):
        """
        Return whether queue is full.

        :returns: True if full, False if not
        """
        return self._queue.full()

    @property
    def qsize(self):
        """
        Return estimate of queue size.

        :returns: Estimate of queue size
        """
        return self._queue.qsize()

    def pause(self):
        """Temporarily pause calling the function."""
        self._event.clear()

    def restart(self):
        """
        Restart Animation.

        Restart calling the function (if paused).  Otherwise this will have no effect.
        """
        self._event.set()

    def toggle(self):
        """Toggle calling the function from on to off or off to on."""
        if self._event.is_set():
            self._event.clear()
        else:
            self._event.set()

    def stop(self):
        """Shut down the animate object including terminating its internal thread."""
        self._running = False
        self._event.set()
        self.get()
        self.join()

    def clear(self):
        """Clear the queue of all curent values."""
        self._emptyQueue()

    def force(self, *args, **kwargs):
        """
        Change the parameters that are passed to the function.

        :param args: The positional arguments to provide to the animated function (optional)
        :type args: tuple
        :param kwargs: The keyword arguments to provide to teh animated function (optional)
        :type kwargs: dict

        ..note:
            force has the side effect of clearing any existing values within the queue.
        """
        self._Force = True

        # Set new arguments for animated function
        self._args = args
        self._kwargs = kwargs

        # If needed, unblock run if the queue if full
        try:
            self._queue.get_nowait()
            self._queue.task_done()
        except Empty:
            pass

        # Wait until animate confirms force is finished
        self._forceEvent.clear()
        self._forceEvent.wait()

    def get(self, wait=0):
        """
        Get the current value from the results queue.

        :param wait: Number of seconds to wait for a response.  If zero (the default)
            return immediately even if no value is currently available
        :type wait: float
        :returns: The current result.  Type of value is determined by what the
            animated function returns.
        :rtype: object

        ..note:
            Be careful with long wait values.  The animate thread will block during
            the wait.  If you attempt to shut down the animate object (using stop),
            it will not finish closing down until the wait has completed.
        """
        try:
            retval = self._queue.get(wait)
            self._queue.task_done()
        except Empty:
            retval = None

        return retval

    def _emptyQueue(self):
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Empty:
                break

    def _invoke(self, *args, **kwargs):
        # Invoke function
        if args and kwargs:
            retval = self._function(*args, **kwargs)
        elif args:
            retval = self._function(*args)
        elif kwargs:
            retval = self._function(**kwargs)
        else:
            retval = self._function()
        return retval

    def run(self):
        """
        Animate function.

        Main loop for the animate thread
        """
        correction = 0
        loopTime = 1 / self._speed
        tpf = 1 / self._speed

        renderTimer = time.time()
        renderCounter = 0
        renderCounterLimit = 1
        self._event.set()
        self._Force = False

        while self._running:

            # Compute current FPS every 5 seconds
            renderCounter += 1
            if renderCounter > renderCounterLimit:
                self.fps = renderCounter / (time.time() - renderTimer)
                renderCounter = 0
                renderCounterLimit = 10
                renderTimer = time.time()

            if not self._event.is_set():
                # Disable pid while waiting to be activated
                self._pid.set_auto_mode(False)
                self._event.wait()
                # Activated!  Re-enable PID, begin processing
                self._pid.set_auto_mode(True, last_output=correction)

            fps = 1 / loopTime  # Time per frame
            correction = self._pid(fps)
            startLoop = time.time()
            tpf = (
                1 / (self._speed + correction)
                if self._speed + correction > 0
                else 0
            )
            time.sleep(tpf)

            # Disable PID while trying to place new render in queue
            putStart = time.time()
            if self._Force:
                self._Force = False
                self._emptyQueue()

                # Must put value in queue before clearing the force Event
                # so that the forced function receives the newly computed value
                try:
                    retval = self._invoke(*self._args, **self._kwargs)
                    self._queue.put(retval)
                except NoResult:
                    pass

                self._forceEvent.set()
            else:
                try:
                    retval = self._invoke(*self._args, **self._kwargs)
                    try:
                        self._queue.put_nowait(retval)
                    except Full:
                        self._pid.set_auto_mode(False)
                        self._queue.put(retval)
                        self._pid.set_auto_mode(True, last_output=correction)
                except NoResult:
                    pass

            # Correct startLoop to account for time blocked by full queue
            startLoop = startLoop + (time.time() - putStart)

            loopTime = time.time() - startLoop 