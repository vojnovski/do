import sys
import time
import subprocess
import digitalocean

TOKEN = 'PUT_YOUR_TOKEN_HERE'
SSH_KEY = 'aa:aa:aa:aa:aa:aa:aa:aa:aa:aa:aa:aa:aa:aa:aa:aa'


def do_off():
    # Get the PID of the ssh tunnel
    command = 'pgrep -f "ssh -f -N -D 12345 -q -o StrictHostKeyChecking=no root"'
    k_output, k_error = subprocess.Popen(command, universal_newlines=True,
                                         shell=True, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE).communicate()
    # Kill the ssh tunnel if existing
    if k_output:
        command = 'kill -9 ' + k_output
        k_output, k_error = subprocess.Popen(command, universal_newlines=True,
                                             shell=True, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE).communicate()
        if k_error:
            subprocess.call(['osascript', '-e', 'display notification "Could not kill SSH ' +
                                                'tunnel, might be a dormant process still running!" ' +
                                                'with title "DigitalOcean Proxy"'])

    # Destroy all my droplets
    manager = digitalocean.Manager(token=TOKEN)
    my_droplets = manager.get_all_droplets()
    for droplet in my_droplets:
        assert droplet.destroy()

    # Set the proxy back to OFF
    proxy_status = subprocess.call('networksetup -setsocksfirewallproxystate Wi-Fi off'.split())

    # Notify with results
    proxy_status_string = '' if proxy_status == 0 else 'COULD NOT '
    notify_command = 'display notification "All ' + str(len(my_droplets)) + \
                     ' Droplets destroyed and ' + proxy_status_string + \
                     'set Proxy OFF" with title "DigitalOcean Proxy"'
    subprocess.call(['osascript', '-e', notify_command])


def do_on():
    # Measure time of execution
    start = time.time()

    # Create droplet
    droplet = digitalocean.Droplet(token=TOKEN,
                                   name='Example',
                                   region='lon1',
                                   image='ubuntu-14-04-x64',
                                   size_slug='512mb',
                                   ssh_keys=[SSH_KEY])
    droplet.create()
    actions = droplet.get_actions()

    # Wait until it finishes loading
    while True:
        action = actions[0]
        action.load()
        if action.status == u'completed':
            break
        time.sleep(1)
    droplet.load()

    # Set the proxy to ON
    proxy_status = subprocess.call('networksetup -setsocksfirewallproxystate Wi-Fi on'.split())

    # Get the IP address of the droplet
    ipaddr = droplet.ip_address

    # Start the ssh tunnel in the background
    ssh_status = subprocess.call(['ssh', '-f', '-N', '-D', '12345', '-q', '-o',
                                  'StrictHostKeyChecking=no', 'root@' + ipaddr])

    # In case of ssh failure, try one more time in 10 seconds
    # Might be that the droplet hasn't booted yet
    if ssh_status != 0:
        ssh_status = subprocess.call(['ssh', '-f', '-N', '-D', '12345', '-q', '-o',
                                      'StrictHostKeyChecking=no', 'root@' + ipaddr])
        time.sleep(10)

    # Give up and notify
    if ssh_status != 0:
        subprocess.call(['osascript', '-e', 'display notification "Could not start SSH ' +
                                            'tunnel, maybe one is already running!" ' +
                                            'with title "DigitalOcean Proxy"'])
        time.sleep(5)  # For reasons unknown, osascript replaces the notif, so we wait a bit

    # Notify with results
    seconds = round(time.time() - start, 0)
    proxy_status_string = '' if proxy_status == 0 else 'COULD NOT '
    notify_command = 'display notification "Created Droplet with ip Address ' + \
                     ipaddr + ' in ' + str(seconds) + ' seconds and ' + \
                     proxy_status_string + 'set Proxy ON" with title "DigitalOcean Proxy"'
    subprocess.call(['osascript', '-e', notify_command])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'off':
        do_off()
    elif len(sys.argv) > 1 and sys.argv[1] == 'on':
        do_on()
    else:
        print "Run with python do.py <on/off>"
