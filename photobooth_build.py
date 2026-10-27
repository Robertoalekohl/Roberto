"""
Build a photobooth network inside TouchDesigner at /project1.

Run in the Textport (save the .toe first so photos land beside the project):

    exec(open(r'C:/path/to/photobooth_build.py', encoding='utf-8').read())

Press 1 or space. The countdown plays over the live camera. At 0 the frame
freezes, one JPEG is written, a white flash fades off, and the live preview
returns after a 3 second review.

Operator classes used here are the modern names (videodevinTOP, fitTOP,
cacheTOP, keyboardinCHOP, timerCHOP, moviefileoutTOP, textTOP, constantTOP,
levelTOP, compositeTOP, chopexecuteDAT, keyboardinDAT).
"""

BOOTH_LOGIC = r'''
import os
import re


def _root():
    return me.parent()


def photo_folder():
    base = project.folder
    if not base:
        desktop = os.path.expanduser('~/Desktop')
        base = desktop if os.path.isdir(desktop) else os.getcwd()
    folder = os.path.join(base, 'photos').replace('\\', '/')
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return folder


def photo_path():
    # Next free booth_####.jpg. Scanning the folder avoids overwriting and
    # does not read Movie File Out's file parameter (that would recurse).
    folder = photo_folder()
    highest = 0
    try:
        names = os.listdir(folder)
    except Exception:
        names = []
    for name in names:
        match = re.match(r'booth_(\d+)\.jpg$', name, re.IGNORECASE)
        if match:
            highest = max(highest, int(match.group(1)))
    return '%s/booth_%04d.jpg' % (folder, highest + 1)


def countdown(running_chan, seconds_chan):
    # Channels are passed in from the Text TOP expression so that TOP
    # recooks every frame the timer is running.
    try:
        running = float(running_chan)
        seconds = float(seconds_chan)
        length = float(_root().op('countdown_timer').par.length.eval())
    except Exception:
        return ''
    if running < 0.5:
        return ''
    # 3 for the first second, then 2, then 1. Blank at 0.
    remaining = int(length) - int(seconds)
    if remaining <= 0:
        return ''
    return str(remaining)


def _running(timer):
    try:
        return float(timer['running'].eval()) >= 0.5
    except Exception:
        return False


def arm_start():
    # One-frame value into the Timer CHOP Start input (input 1).
    root = _root()
    cache = root.op('photo_cache')
    timer = root.op('countdown_timer')
    if cache is None or timer is None:
        return False
    if not bool(cache.par.active.eval()):
        return False
    if _running(timer):
        return False
    pulse = root.op('start_pulse')
    pulse.par.const0value = 1
    try:
        timer.cook(force=True)
    except Exception:
        pass
    run('args[0].par.const0value = 0', pulse, delayFrames=1, group='photobooth')
    return True


def shutter():
    if arm_start():
        print('photobooth: shutter')
    else:
        print('photobooth: shutter ignored (countdown or review in progress)')


def capture(timerOp):
    root = timerOp.parent()
    cache = root.op('photo_cache')
    writer = root.op('image_writer')
    flash = root.op('flash_trigger')

    # Capture the current camera frame, then hold it.
    cache.par.active = True
    try:
        cache.cook(force=True)
    except Exception as err:
        print('photobooth: camera cook failed (%s)' % err)
    cache.par.active = False

    path = writer.par.file.eval()
    print('photobooth: writing %s' % path)
    writer.par.record = True
    try:
        writer.cook(force=True)
    except Exception as err:
        print('photobooth: image cook failed (%s)' % err)
    run('args[0].par.record = False', writer, delayFrames=1, group='photobooth')

    # Snap the white plate on. flash_lag eases it back down over ~15 frames.
    flash.par.const0value = 1
    run('args[0].par.const0value = 0', flash, delayFrames=1, group='photobooth')

    token = int(root.fetch('review_token', 0)) + 1
    root.store('review_token', token)
    rate = root.time.rate or 60
    frames = max(1, int(round(3 * float(rate))))
    run(
        'root, token = args\n'
        'if root.valid and int(root.fetch("review_token", -1)) == int(token):\n'
        '    root.op("photo_cache").par.active = True\n',
        root,
        token,
        delayFrames=frames,
        group='photobooth',
    )
'''

TIMER_CALLBACKS = r'''
def onStart(timerOp):
    root = timerOp.parent()
    # Drop any review-window callback left over from the previous shot.
    root.store('review_token', int(root.fetch('review_token', 0)) + 1)
    root.op('photo_cache').par.active = True
    return


def onDone(timerOp, segment, interrupt):
    timerOp.parent().op('booth_logic').module.capture(timerOp)
    return
'''

KEY_CALLBACKS = r'''
def _is_down(state):
    if isinstance(state, str):
        return state.lower() in ('1', 'down', 'press', 'true', 'on')
    return bool(state)


def _key_and_state(args, kwargs):
    key = kwargs.get('key', None)
    state = kwargs.get('state', None)
    if not args:
        return key, state
    first = args[0]
    if not isinstance(first, str) and (hasattr(first, 'key') or hasattr(first, 'state')):
        if key is None:
            key = getattr(first, 'key', None)
        if state is None:
            state = getattr(first, 'state', None)
        return key, state
    if key is None:
        key = first
    # Classic Keyboard In DAT callback:
    # key, character, alt, lAlt, rAlt, ctrl, lCtrl, rCtrl, shift, lShift, rShift, state, time
    if state is None and len(args) >= 12:
        state = args[11]
    return key, state


def onKey(dat, *args, **kwargs):
    key, state = _key_and_state(args, kwargs)
    if key != 'space' or not _is_down(state):
        return
    # Keyboard In CHOP cannot emit the space bar. Fold space into the same
    # channel the "1" key drives, for a single frame.
    pulse = me.parent().op('space_pulse')
    pulse.par.const0value = 1
    run('args[0].par.const0value = 0', pulse, delayFrames=1, group='photobooth')
    return


def onShortcut(dat, shortcutName, time):
    return
'''

TRIGGER_CALLBACKS = r'''
def onOffToOn(channel, sampleIndex, val, prev):
    me.parent().op('booth_logic').module.arm_start()
    return


def whileOn(channel, sampleIndex, val, prev):
    return


def onOnToOff(channel, sampleIndex, val, prev):
    return


def whileOff(channel, sampleIndex, val, prev):
    return


def onValueChange(channel, sampleIndex, val, prev):
    return
'''

README = """Photobooth

Trigger: 1 key, space bar, or:
    op('/project1/booth_logic').module.shutter()

Flow:
  1. countdown_timer runs for 3 seconds.
     final_output shows the live camera plus 3, 2, 1.
  2. onDone freezes photo_cache (Active off), pulses image_writer Record,
     and snaps flash_level opacity to 1.
  3. flash_lag fades that opacity back to 0 over about 15 frames.
  4. After 3 seconds photo_cache Active turns back on.

JPEGs: <project folder>/photos/booth_0001.jpg and up.
Save the .toe so project.folder is the project directory.
On cam_input, pick the camera if the default device is wrong.
The timeline has to be playing.
"""

NODE_NAMES = (
    'cam_input',
    'fit_to_screen',
    'photo_cache',
    'image_writer',
    'countdown_text',
    'flash_white',
    'flash_level',
    'comp_countdown',
    'final_output',
    'trigger_key',
    'trigger_rename',
    'trigger_space',
    'trigger_space_callbacks',
    'space_pulse',
    'trigger_mix',
    'trigger_exec',
    'start_pulse',
    'countdown_timer',
    'countdown_callbacks',
    'flash_trigger',
    'flash_lag',
    'booth_logic',
    'booth_readme',
)


def _in_touchdesigner():
    try:
        import td  # noqa: F401
    except Exception:
        return False
    return True


def set_menu(par, *candidates, **kwargs):
    required = kwargs.get('required', True)
    if not getattr(par, 'isMenu', False):
        par.val = candidates[0]
        return True
    names = list(par.menuNames)
    for candidate in candidates:
        if candidate in names:
            par.val = candidate
            return True
    if required:
        raise Exception(
            '%s.%s: none of %s are valid. Options: %s'
            % (par.owner.path, par.name, candidates, names)
        )
    return False


def set_flag(par, value):
    if getattr(par, 'isMenu', False):
        if value:
            set_menu(par, 'on', 'true', 'always', 1)
        else:
            set_menu(par, 'off', 'false', 'never', 0)
    else:
        par.val = bool(value)


def top_resolution(node, width, height):
    set_menu(node.par.outputresolution, 'custom')
    node.par.resolutionw = width
    node.par.resolutionh = height
    if hasattr(node.par, 'resmult'):
        node.par.resmult = False


def place(node, x, y):
    node.nodeX = x
    node.nodeY = y


def fill_dat(node, text):
    node.text = text
    if hasattr(node.par, 'language') and getattr(node.par.language, 'isMenu', False):
        set_menu(node.par.language, 'python', required=False)


def op_class(name, fallback=None):
    import td
    for source in (globals(), getattr(td, '__dict__', {})):
        if name in source and source[name] is not None:
            return source[name]
    found = getattr(td, name, None)
    if found is not None:
        return found
    if fallback:
        return op_class(fallback)
    raise Exception('TouchDesigner has no operator class %s' % name)


def connect_start(timer, source):
    chosen = None
    for conn in timer.inputConnectors:
        label = ''
        for attr in ('label', 'description'):
            if hasattr(conn, attr) and getattr(conn, attr):
                label = str(getattr(conn, attr))
                break
        if 'start' in label.lower():
            chosen = conn
            break
    if chosen is None:
        if len(timer.inputConnectors) < 2:
            raise Exception('countdown_timer is missing its Start input (input 1).')
        chosen = timer.inputConnectors[1]
    chosen.connect(source)


def kill_pending():
    try:
        pending = list(runs)
    except Exception:
        return
    for item in pending:
        try:
            if item.group == 'photobooth':
                item.kill()
        except Exception:
            pass


def build():
    kill_pending()

    root = op('/project1')
    if root is None:
        root = op('/').create(op_class('baseCOMP'), 'project1')

    for name in NODE_NAMES:
        node = root.op(name)
        if node is not None:
            node.destroy()

    cam_type = 'videodevinTOP'
    try:
        cam_class = op_class('videodevinTOP')
    except Exception:
        cam_class = op_class('videoinTOP')
        cam_type = 'videoinTOP'

    cam = root.create(cam_class, 'cam_input')
    fit = root.create(op_class('fitTOP'), 'fit_to_screen')
    cache = root.create(op_class('cacheTOP'), 'photo_cache')
    writer = root.create(op_class('moviefileoutTOP'), 'image_writer')
    countdown = root.create(op_class('textTOP'), 'countdown_text')
    white = root.create(op_class('constantTOP'), 'flash_white')
    level = root.create(op_class('levelTOP'), 'flash_level')
    comp = root.create(op_class('compositeTOP'), 'comp_countdown')
    final = root.create(op_class('compositeTOP'), 'final_output')

    trigger_key = root.create(op_class('keyboardinCHOP'), 'trigger_key')
    trigger_rename = root.create(op_class('renameCHOP'), 'trigger_rename')
    trigger_space = root.create(op_class('keyboardinDAT'), 'trigger_space')
    space_callbacks = root.create(op_class('textDAT'), 'trigger_space_callbacks')
    space_pulse = root.create(op_class('constantCHOP'), 'space_pulse')
    trigger_mix = root.create(op_class('mathCHOP'), 'trigger_mix')
    trigger_exec = root.create(op_class('chopexecuteDAT'), 'trigger_exec')
    start_pulse = root.create(op_class('constantCHOP'), 'start_pulse')
    timer = root.create(op_class('timerCHOP'), 'countdown_timer')
    timer_callbacks = root.create(op_class('textDAT'), 'countdown_callbacks')

    flash_trigger = root.create(op_class('constantCHOP'), 'flash_trigger')
    flash_lag = root.create(op_class('lagCHOP'), 'flash_lag')
    logic = root.create(op_class('textDAT'), 'booth_logic')
    readme = root.create(op_class('textDAT'), 'booth_readme')

    place(cam, -1100, 400)
    place(fit, -860, 400)
    place(cache, -620, 400)
    place(writer, -620, 140)
    place(countdown, -200, 680)
    place(comp, -200, 400)
    place(white, 220, 920)
    place(level, 220, 680)
    place(final, 220, 400)
    place(trigger_key, -1100, -40)
    place(trigger_rename, -860, -40)
    place(trigger_space, -1100, -280)
    place(space_callbacks, -1100, -460)
    place(space_pulse, -860, -280)
    place(trigger_mix, -600, -140)
    place(trigger_exec, -360, -140)
    place(start_pulse, -120, -140)
    place(timer, 140, -140)
    place(timer_callbacks, 140, -400)
    place(flash_trigger, 220, 80)
    place(flash_lag, 480, 80)
    place(logic, 740, 140)
    place(readme, 740, 400)

    # Camera -> 1920x1080 frame -> 1-frame cache. Active on means live video.
    set_flag(cam.par.active, True)
    top_resolution(fit, 1920, 1080)
    set_menu(fit.par.fit, 'fill', 'fitbest', 'fitoutside')
    if hasattr(fit.par, 'justifyh'):
        set_menu(fit.par.justifyh, 'center', required=False)
    if hasattr(fit.par, 'justifyv'):
        set_menu(fit.par.justifyv, 'center', required=False)

    set_flag(cache.par.active, True)
    cache.par.cachesize = 1
    cache.par.outputindex = 0
    if hasattr(cache.par, 'cacheonce'):
        cache.par.cacheonce = True

    # Single JPEG, unique name, record held for one frame only.
    set_menu(writer.par.type, 'image')
    set_menu(writer.par.imagefiletype, 'jpeg')
    if hasattr(writer.par, 'uniquesuff'):
        writer.par.uniquesuff = False
    writer.par.record = False
    if hasattr(writer.par, 'limitlength'):
        writer.par.limitlength = True
        writer.par.length = 1
        set_menu(writer.par.lengthunit, 'frames', 'frame')

    top_resolution(countdown, 1920, 1080)
    if hasattr(countdown.par, 'fontautosize'):
        set_menu(countdown.par.fontautosize, 'nofit', required=False)
    pixel_units = False
    if hasattr(countdown.par, 'fontsizexunit'):
        pixel_units = set_menu(countdown.par.fontsizexunit, 'pixels', 'pixel', required=False)
    if hasattr(countdown.par, 'fontsizex'):
        countdown.par.fontsizex = 340 if pixel_units or not hasattr(countdown.par, 'fontsizexunit') else 0.25
    if hasattr(countdown.par, 'keepfontratio'):
        countdown.par.keepfontratio = True
    if hasattr(countdown.par, 'alignx'):
        set_menu(countdown.par.alignx, 'center')
    if hasattr(countdown.par, 'aligny'):
        set_menu(countdown.par.aligny, 'center')
    if hasattr(countdown.par, 'alignxmode'):
        set_menu(countdown.par.alignxmode, 'bbox', required=False)
    if hasattr(countdown.par, 'alignymode'):
        set_menu(countdown.par.alignymode, 'bbox', required=False)
    if hasattr(countdown.par, 'position1'):
        countdown.par.position1 = 0.5
        countdown.par.position2 = 0.5
    if hasattr(countdown.par, 'positionunit'):
        set_menu(countdown.par.positionunit, 'fraction', 'frac', required=False)
    if hasattr(countdown.par, 'dispmethod'):
        set_menu(countdown.par.dispmethod, 'polygon', required=False)
    countdown.par.fontcolorr = 1
    countdown.par.fontcolorg = 1
    countdown.par.fontcolorb = 1
    if hasattr(countdown.par, 'fontalpha'):
        countdown.par.fontalpha = 1
    if hasattr(countdown.par, 'bgalpha'):
        countdown.par.bgalpha = 0
    countdown.par.text.expr = (
        "op('booth_logic').module.countdown("
        "op('countdown_timer')['running'], "
        "op('countdown_timer')['timer_seconds'])"
    )

    top_resolution(white, 1920, 1080)
    white.par.colorr = 1
    white.par.colorg = 1
    white.par.colorb = 1
    white.par.alpha = 1

    level.par.opacity = 0
    if hasattr(level.par, 'premultrgbbyalpha'):
        level.par.premultrgbbyalpha = True
    level.par.opacity.expr = "op('flash_lag')['opacity'].eval()"

    for node in (comp, final):
        top_resolution(node, 1920, 1080)
        set_menu(node.par.operand, 'over')
        if hasattr(node.par, 'size'):
            set_menu(node.par.size, 'input2', required=False)

    # Key "1" is the Keyboard In CHOP. Space is merged in from a DAT because
    # the CHOP keys menu is only 0-9, A-Z, and the keypad.
    set_menu(trigger_key.par.active, 'on')
    trigger_key.par.keys = '1'
    if hasattr(trigger_key.par, 'modifiers'):
        set_menu(trigger_key.par.modifiers, 'ignore', required=False)
    if hasattr(trigger_key.par, 'channelnames'):
        set_menu(trigger_key.par.channelnames, 'key', required=False)
    trigger_rename.par.renamefrom = '*'
    trigger_rename.par.renameto = 'trigger'

    set_flag(trigger_space.par.active, True)
    if hasattr(trigger_space.par, 'perform'):
        trigger_space.par.perform = False
    trigger_space.par.keys = 'space'
    if hasattr(trigger_space.par, 'clamp'):
        trigger_space.par.clamp = True
    if hasattr(trigger_space.par, 'maxlines'):
        trigger_space.par.maxlines = 20
    fill_dat(space_callbacks, KEY_CALLBACKS)
    trigger_space.par.callbacks = space_callbacks
    space_callbacks.dock = trigger_space

    space_pulse.par.const0name = 'trigger'
    space_pulse.par.const0value = 0
    set_menu(trigger_mix.par.chopop, 'max')
    if hasattr(trigger_mix.par, 'chanop'):
        set_menu(trigger_mix.par.chanop, 'off', required=False)
    if hasattr(trigger_mix.par, 'match'):
        set_menu(trigger_mix.par.match, 'index', 'name', required=False)

    fill_dat(trigger_exec, TRIGGER_CALLBACKS)
    trigger_exec.par.chop = trigger_mix
    set_flag(trigger_exec.par.active, True)
    set_flag(trigger_exec.par.offtoon, True)
    for name in ('whileon', 'ontooff', 'whileoff', 'valuechange'):
        if hasattr(trigger_exec.par, name):
            set_flag(getattr(trigger_exec.par, name), False)

    start_pulse.par.const0name = 'start'
    start_pulse.par.const0value = 0

    set_menu(timer.par.active, 'always')
    if hasattr(timer.par, 'timecontrol'):
        set_menu(timer.par.timecontrol, 'sequential', required=False)
    if hasattr(timer.par, 'lengthtype'):
        set_menu(timer.par.lengthtype, 'fixed', required=False)
    timer.par.length = 3
    set_menu(timer.par.lengthunits, 'seconds')
    if hasattr(timer.par, 'runvalues'):
        set_menu(timer.par.runvalues, 'zero', required=False)
    if hasattr(timer.par, 'cycle'):
        timer.par.cycle = False
    if hasattr(timer.par, 'ondone'):
        set_menu(timer.par.ondone, 'donothing', required=False)
    if hasattr(timer.par, 'deferpars'):
        timer.par.deferpars = False
    if hasattr(timer.par, 'play'):
        set_flag(timer.par.play, True)
    set_menu(timer.par.outtimercount, 'seconds')
    set_flag(timer.par.outrunning, True)
    if hasattr(timer.par, 'outdone'):
        set_flag(timer.par.outdone, True)
    fill_dat(timer_callbacks, TIMER_CALLBACKS)
    timer.par.callbacks = timer_callbacks
    timer_callbacks.dock = timer
    timer.par.initialize.pulse()

    flash_trigger.par.const0name = 'opacity'
    flash_trigger.par.const0value = 0
    set_menu(flash_lag.par.lagmethod, 'value')
    flash_lag.par.lag1 = 0
    flash_lag.par.lag2 = 15
    set_menu(flash_lag.par.lagunit, 'frames', 'frame')
    flash_lag.par.overshoot1 = 0
    flash_lag.par.overshoot2 = 0
    if hasattr(flash_lag.par, 'snap'):
        flash_lag.par.snap = True
    if hasattr(flash_lag.par, 'threshold'):
        flash_lag.par.threshold = 0.02
    if hasattr(flash_lag.par, 'timeslice'):
        flash_lag.par.timeslice = False

    fill_dat(logic, BOOTH_LOGIC)
    fill_dat(readme, README)
    writer.par.file.expr = "op('booth_logic').module.photo_path()"

    fit.inputConnectors[0].connect(cam)
    cache.inputConnectors[0].connect(fit)
    writer.inputConnectors[0].connect(cache)
    # Over: connector 0 is the top layer, connector 1 is behind it.
    comp.inputConnectors[0].connect(countdown)
    comp.inputConnectors[1].connect(cache)
    level.inputConnectors[0].connect(white)
    final.inputConnectors[0].connect(level)
    final.inputConnectors[1].connect(comp)

    trigger_rename.inputConnectors[0].connect(trigger_key)
    trigger_mix.inputConnectors[0].connect(trigger_rename)
    trigger_mix.inputConnectors[1].connect(space_pulse)
    connect_start(timer, start_pulse)
    flash_lag.inputConnectors[0].connect(flash_trigger)

    try:
        flash_trigger.cook(force=True)
        flash_lag.cook(force=True)
        timer.cook(force=True)
    except Exception as err:
        print('photobooth: initial cook skipped (%s)' % err)

    final.viewer = True
    cache.viewer = True
    try:
        final.display = True
    except Exception:
        pass
    try:
        final.color = (0.15, 0.35, 0.55)
    except Exception:
        pass
    try:
        root.current = True
    except Exception:
        pass

    folder = ''
    try:
        folder = logic.module.photo_folder()
    except Exception as err:
        folder = '(unavailable: %s)' % err

    print('')
    print('Photobooth is in %s' % root.path)
    print('Camera class: %s' % cam_type)
    print('Watch final_output. Trigger with the 1 key, space, or:')
    print("    op('%s/booth_logic').module.shutter()" % root.path)
    print('JPEGs: %s' % folder)
    print('Timeline must be playing. Pick the device on cam_input if needed.')
    return root


def _check_dat_sources():
    for label, source in (
        ('booth_logic', BOOTH_LOGIC),
        ('timer_callbacks', TIMER_CALLBACKS),
        ('key_callbacks', KEY_CALLBACKS),
        ('trigger_callbacks', TRIGGER_CALLBACKS),
    ):
        compile(source, '<%s>' % label, 'exec')


if _in_touchdesigner():
    build()
else:
    _check_dat_sources()
