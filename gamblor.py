#! /usr/bin/env python3


import re
import schedule
import secrets
import signal
import sys
import time
import unittest

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

import config


points = 0
wager = 1
winner = True


def setup():
    options = webdriver.ChromeOptions()
    options.add_argument('--incognito')
    options.add_argument('--mute-audio')
    options.headless = config.headless
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    # driver.maximize_window()
    driver.get(config.twitch_url)

    # Login with username/password
    try:
        WebDriverWait(driver, 30).until(expected_conditions.visibility_of_element_located((By.XPATH, '//button[@data-test-selector="anon-user-menu__login-button"]')))
    except WebDriverException:
        print('COULD NOT FIND LOGIN BUTTON!')
        raise WebDriverException
    driver.find_element(By.XPATH, '//button[@data-test-selector="anon-user-menu__login-button"]').click()
    try:
        WebDriverWait(driver, 30).until(
            expected_conditions.visibility_of_element_located((By.XPATH, '//div[@data-a-target="login-username-input"]')))
    except WebDriverException:
        print('COULD NOT FIND USERNAME FIELD!')
        raise WebDriverException
    driver.find_element(By.XPATH, '//div[@data-a-target="login-username-input"]').click()
    driver.find_element(By.XPATH, '//input[@id="login-username"]').send_keys(config.username)
    driver.find_element(By.XPATH, '//div[@data-a-target="login-password-input"]').click()
    driver.find_element(By.XPATH, '//input[@id="password-input"]').send_keys(config.password)
    driver.find_element(By.XPATH, '//button[@data-a-target="passport-login-button"]').click()

    # Get user input for 2-factor authentication
    # try:
    #     WebDriverWait(driver, 300).until(expected_conditions.visibility_of_element_located((By.XPATH, '//div[text()="Request SMS"]')))
    #     driver.find_element(By.XPATH, '//div[text()="Request SMS"]').click()
    # except WebDriverException:
    #     pass
    code = input('2fa code: ')
    try:
        driver.find_element(By.XPATH, '//input[@inputmode="numeric"]').send_keys(code)
        driver.find_element(By.XPATH, '//input[@inputmode="numeric"]').send_keys(Keys.ENTER)
    except WebDriverException:
        pass
    return driver


def gamble():
    suite = unittest.TestSuite()
    suite.addTest(Gamblor('gamble'))
    unittest.TextTestRunner().run(suite)


def gift():
    suite = unittest.TestSuite()
    suite.addTest(Gamblor('gift'))
    unittest.TextTestRunner().run(suite)


def set_winner(result):
    global winner
    winner = result


def reset_wager():
    global wager
    points = check_points()
    print(f'points: {str(points)}')
    for i in range(config.loss_tolerance):
        points = points // 2
    if points < 2:
        wager = 1
    else:
        wager = points


def double_wager():
    global wager
    wager = wager * 2


def check_points():
    options = webdriver.ChromeOptions()
    options.add_argument('--incognito')
    options.add_argument('--mute-audio')
    options.headless = True
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    # driver.maximize_window()
    driver.get(config.leaderboard_url)

    # Search for username
    WebDriverWait(driver, 30).until(expected_conditions.visibility_of_element_located((By.XPATH, '//form[@name="searchForm"]')))
    driver.find_element(By.XPATH, '//form[@name="searchForm"]').click()
    driver.find_element(By.XPATH, '//input[@name="search"]').send_keys(config.username)
    driver.find_element(By.XPATH, '//input[@name="search"]').send_keys(Keys.ENTER)
    driver.find_element(By.XPATH, '//input[@name="search"]').send_keys(Keys.ENTER)
    try:
        WebDriverWait(driver, 30).until(expected_conditions.visibility_of_element_located((By.XPATH, '//md-card[@ng-if="vm.searchResult && vm.isSearching === false"]')))
        points = int(re.search('^Points: (\d+)', driver.find_element(By.XPATH, '//md-card[@ng-if="vm.searchResult && vm.isSearching === false"]/div/div[last()]/h3').text).group(1))
    except WebDriverException:
        points = 0
    driver.quit()
    return points


def signal_handler(signal, frame):
    sys.exit()


class Gamblor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print('\nstarting...')

    @classmethod
    def tearDownClass(cls):
        print('\nfinishing up...')

    def tearDown(self):
        self.result = self.defaultTestResult()
        self._feedErrorsToResult(self.result, self._outcome.errors)
        if (len(self.result.failures) != 0) or (len(self.result.errors) != 0):
            driver.save_screenshot(f'{config.screenshot_path}error.png')

    def gamble(self):
        global wager
        global winner
        if winner:
            reset_wager()
            print(f'betting the base wager ({wager})...')
        else:
            double_wager()
            print(f'betting bigger ({wager})...')
            self.points = check_points()
            if wager > self.points:
                wager = self.points

        # If chat list is not visible, click on the streamer's name
        try:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, '//div[contains(@class, "chat-input__textarea")]')))
        except WebDriverException:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, f'//h1[text()="{config.twitch_streamer}"]')))
            driver.find_element(By.XPATH, f'//h1[text()="{config.twitch_streamer}"]').click()
            time.sleep(3)
        try:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, '//button[@class="tw-button tw-button--success tw-interactive"]')))
            driver.find_element(By.XPATH, '//button[@class="tw-button tw-button--success tw-interactive"]').click()
        except WebDriverException:
            pass

        # Find chat box
        self.chatbox = driver.find_element(By.XPATH, '//div[contains(@class, "chat-input__textarea")]')

        # Check for a chat rules popup
        self.chatbox.click()
        try:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, '//button[@data-test-selector="chat-rules-ok-button"]')))
            driver.find_element(By.XPATH, '//button[@data-test-selector="chat-rules-ok-button"]').click()
        except WebDriverException:
            pass

        # Gamble!
        self.chatbox.click()
        self.message = f'!gamble {str(wager)}'
        print(self.message)
        driver.find_element(By.XPATH, '//textarea[@data-test-selector="chat-input"]').send_keys(self.message)
        driver.find_element(By.XPATH, '//button[@data-a-target="chat-send-button"]').click()
        time.sleep(3)

        # Check for results
        self.result_elements = driver.find_elements(By.XPATH, '//div[@data-test-selector="chat-line-message"]')
        for result_element in reversed(self.result_elements):
            self.result_text = result_element.text
            if ('StreamElements' in self.result_text) and (config.username in self.result_text):
                print(self.result_text)
                if 'lost' in self.result_text:
                    set_winner(False)
                else:
                    set_winner(True)
                break
        if winner:
            print('so far, so good...')
        else:
            print('need to up the stakes...')


    def gift(self):
        # If chat list is not visible, click on the streamer's name
        try:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, '//div[contains(@class, "chat-input__textarea")]')))
        except WebDriverException:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, f'//h1[text()="{config.twitch_streamer}"]')))
            driver.find_element(By.XPATH, f'//h1[text()="{config.twitch_streamer}"]').click()
            time.sleep(3)
        try:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, '//button[@class="tw-button tw-button--success tw-interactive"]')))
            driver.find_element(By.XPATH, '//button[@class="tw-button tw-button--success tw-interactive"]').click()
        except WebDriverException:
            pass

        # Find chat box
        self.chatbox = driver.find_element(By.XPATH, '//div[contains(@class, "chat-input__textarea")]')

        # Check for a chat rules popup
        self.chatbox.click()
        try:
            WebDriverWait(driver, 1).until(expected_conditions.visibility_of_element_located((By.XPATH, '//button[@data-test-selector="chat-rules-ok-button"]')))
            driver.find_element(By.XPATH, '//button[@data-test-selector="chat-rules-ok-button"]').click()
        except WebDriverException:
            pass

        # Check the current chat users
        self.userlistbutton = driver.find_element(By.XPATH, '//button[@data-test-selector="chat-viewer-list"]')
        self.userlistbutton.click()
        time.sleep(3)
        self.users = driver.find_elements(By.XPATH, '//button[@data-test-selector="chat-viewers-list__button"]')
        while True:
            self.recipient = secrets.choice(self.users).get_attribute('data-username')
            if config.username not in self.recipient:
                break
        self.userlistbutton.click()

        # Send a gift!
        print(f'gifting {config.gift_size} to {self.recipient}...')
        self.chatbox.click()
        time.sleep(3)
        self.message = f'!givepoints @{self.recipient} {str(config.gift_size)}'
        print(self.message)
        driver.find_element(By.XPATH, '//textarea[@data-test-selector="chat-input"]').send_keys(self.message)
        driver.find_element(By.XPATH, '//button[@data-a-target="chat-send-button"]').click()
        time.sleep(3)

        # Check for results
        self.result_elements = driver.find_elements(By.XPATH, '//div[@data-test-selector="chat-line-message"]')
        for result_element in reversed(self.result_elements):
            self.result_text = result_element.text
            if ('StreamElements' in self.result_text) and (config.username in self.result_text) and (self.recipient in self.result_text):
                print(self.result_text)
                break


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    driver = setup()
    schedule.every(config.gambling_interval_seconds).seconds.do(gamble)
    schedule.every(config.gift_interval_seconds).seconds.do(gift)
    while True:
        schedule.run_pending()
        time.sleep(1)

