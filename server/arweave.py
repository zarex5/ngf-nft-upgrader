import subprocess


def send_to_arweave(path, passcode):
    test = subprocess.run(['arweave', 'deploy', str(path), '--force-skip-confirmation', '--force-skip-warnings'],
                   capture_output=True, text=True, input=passcode)
    res = test.stdout
    link = res.split("following URL\n\n")[1].split("\n\nYou can check")[0]
    return link
