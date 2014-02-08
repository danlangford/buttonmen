<?php

class BMInterfaceTest extends PHPUnit_Framework_TestCase {

    /**
     * @var BMInterface
     */
    protected $object;
    private static $userId1WithoutAutopass;
    private static $userId2WithoutAutopass;
    private static $userId3WithAutopass;
    private static $userId4WithAutopass;

    /**
     * Sets up the fixture, for example, opens a network connection.
     * This method is called before a test is executed.
     */
    protected function setUp() {
        if (file_exists('../test/src/database/mysql.test.inc.php')) {
            require_once '../test/src/database/mysql.test.inc.php';
        } else {
            require_once 'test/src/database/mysql.test.inc.php';
        }
        $this->object = new BMInterface(TRUE);
    }

    /**
     * Tears down the fixture, for example, closes a network connection.
     * This method is called after a test is executed.
     */
    protected function tearDown() {

    }

    /**
     * @covers BMInterface::create_user
     */
    public function test_create_user() {
        $created_real = False;
        $maxtries = 999;
        $trynum = 1;

        // Tests may be run multiple times.  Find a user of the
        // form interfaceNNN which hasn't been created yet and
        // create it in the test DB.  The dummy interface will claim
        // success for any username of this form.
        while (!($created_real)) {
            $this->assertTrue($trynum < $maxtries,
                "Internal test error: too many interfaceNNN users in the test database. " .
                "Clean these out by hand.");
            $username = 'interface' . sprintf('%03d', $trynum);
            $createResult = $this->object->create_user($username, 't');
            if (isset($createResult)) {
                $created_real = True;
            }
            $trynum++;
        }

        $this->assertTrue($created_real,
            "Creation of $username user should be reported as success");
        self::$userId1WithoutAutopass = (int)$createResult['playerId'];

        $username = 'interface' . sprintf('%03d', $trynum);
        $createResult = $this->object->create_user($username, 't');
        self::$userId2WithoutAutopass = (int)$createResult['playerId'];

        $trynum++;
        $username = 'interface' . sprintf('%03d', $trynum);
        $createResult = $this->object->create_user($username, 't');
        $this->object->set_player_info($createResult['playerId'],
                                       array('autopass' => 1));
        self::$userId3WithAutopass = (int)$createResult['playerId'];

        $trynum++;
        $username = 'interface' . sprintf('%03d', $trynum);
        $createResult = $this->object->create_user($username, 't');
        $this->object->set_player_info($createResult['playerId'],
                                       array('autopass' => 1));
        self::$userId4WithAutopass = (int)$createResult['playerId'];
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::get_player_info
     */
    public function test_get_player_info() {
        $resultArray = $this->object->get_player_info(1, array('autopass'));
        $this->assertTrue(is_array($resultArray));

        $this->assertArrayHasKey('id', $resultArray);
        $this->assertArrayHasKey('name_ingame', $resultArray);
        $this->assertArrayNotHasKey('password_hashed', $resultArray);
        $this->assertArrayHasKey('name_irl', $resultArray);
        $this->assertArrayHasKey('email', $resultArray);
        $this->assertArrayHasKey('dob', $resultArray);
        $this->assertArrayHasKey('autopass', $resultArray);
        $this->assertArrayHasKey('image_path', $resultArray);
        $this->assertArrayHasKey('comment', $resultArray);
        $this->assertArrayHasKey('last_action_time', $resultArray);
        $this->assertArrayHasKey('creation_time', $resultArray);
        $this->assertArrayHasKey('fanatic_button_id', $resultArray);
        $this->assertArrayHasKey('n_games_won', $resultArray);
        $this->assertArrayHasKey('n_games_lost', $resultArray);

        $this->assertTrue(is_int($resultArray['id']));
        $this->assertEquals(1, $resultArray['id']);

        $this->assertTrue(is_bool($resultArray['autopass']));

        $this->assertTrue(is_int($resultArray['fanatic_button_id']));
        $this->assertEquals(0, $resultArray['fanatic_button_id']);
        $this->assertTrue(is_int($resultArray['n_games_won']));
        $this->assertTrue(is_int($resultArray['n_games_lost']));
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::get_player_info
     * @covers BMInterface::set_player_info
     */
    public function test_set_player_info() {
        $this->object->set_player_info(self::$userId1WithoutAutopass,
                                       array('autopass' => 1));
        $playerInfoArray = $this->object->get_player_info(self::$userId1WithoutAutopass);
        $this->assertEquals(TRUE, $playerInfoArray['autopass']);

        $this->object->set_player_info(self::$userId1WithoutAutopass,
                                       array('autopass' => 0));
        $playerInfoArray = $this->object->get_player_info(self::$userId1WithoutAutopass);
        $this->assertEquals(FALSE, $playerInfoArray['autopass']);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::create_game
     * @covers BMInterface::load_game
     */
    public function test_create_and_load_new_game() {
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                             array('Bauer', 'Stark'), 4);
        $gameId = $retval['gameId'];

        $game = $this->object->load_game($gameId);

        // check player info
        $this->assertCount(2, $game->playerIdArray);
        $this->assertEquals(2, $game->nPlayers);
        $this->assertEquals(self::$userId1WithoutAutopass, $game->playerIdArray[0]);
        $this->assertEquals(self::$userId2WithoutAutopass, $game->playerIdArray[1]);
        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);
        $this->assertFalse(isset($game->activePlayerIdx));
        $this->assertFalse(isset($game->playerWithInitiativeIdx));
        $this->assertFalse(isset($game->attackerPlayerIdx));
        $this->assertFalse(isset($game->defenderPlayerIdx));
        $this->assertEquals(array(FALSE, FALSE), $game->isPrevRoundWinnerArray);

        // check buttons
        $this->assertCount(2, $game->buttonArray);
        $this->assertTrue(is_a($game->buttonArray[0], 'BMButton'));
        $this->assertEquals('Bauer', $game->buttonArray[0]->name);
        $this->assertEquals('(8) (10) (12) (20) (X)', $game->buttonArray[0]->recipe);

        $this->assertTrue(is_a($game->buttonArray[1], 'BMButton'));
        $this->assertEquals('Stark', $game->buttonArray[1]->name);
        $this->assertEquals('(4) (6) (8) (X) (X)', $game->buttonArray[1]->recipe);

        // check dice
        $this->assertTrue(isset($game->activeDieArrayArray));
        $this->assertCount(2, $game->activeDieArrayArray);

        $expectedRecipes = array(array('(8)', '(10)', '(12)', '(20)', '(X)'),
                                 array('(4)', '(6)', '(8)', '(X)', '(X)'));
        $expectedSizes = array(array(8, 10, 12, 20, NAN),
                               array(4, 6, 8, NAN, NAN));
        foreach ($game->activeDieArrayArray as $playerIdx => $activeDieArray) {
            $this->assertEquals(count($expectedRecipes[$playerIdx]),
                                count($activeDieArray));
            for ($dieIdx = 0; $dieIdx <= 4; $dieIdx++) {
                $this->assertEquals($expectedRecipes[$playerIdx][$dieIdx],
                                    $activeDieArray[$dieIdx]->recipe);
                if (is_nan($expectedSizes[$playerIdx][$dieIdx])) {
                    $this->assertFalse(isset($activeDieArray[$dieIdx]->max));
                    $this->assertFalse(isset($activeDieArray[$dieIdx]->value));
                } else {
                    $this->assertEquals($expectedSizes[$playerIdx][$dieIdx],
                                        $activeDieArray[$dieIdx]->max);
                    $this->assertTrue(isset($activeDieArray[$dieIdx]->value));
                }
            }
        }

        $this->assertFalse(isset($game->attackerAllDieArray));
        $this->assertFalse(isset($game->defenderAllDieArray));
        $this->assertFalse(isset($game->attackerAttackDieArray));
        $this->assertFalse(isset($game->attackerAttackDieArray));
        $this->assertFalse(isset($game->auxiliaryDieDecisionArrayArray));
        $this->assertEquals(array(array(), array()), $game->capturedDieArrayArray);

        // check swing details
        $this->assertTrue(isset($game->swingRequestArrayArray));
        $this->assertCount(2, $game->swingRequestArrayArray);
        $this->assertCount(1, $game->swingRequestArrayArray[0]);
        $this->assertTrue(array_key_exists('X', $game->swingRequestArrayArray[0]));
        $this->assertCount(1, $game->swingRequestArrayArray[0]['X']);
        $this->assertTrue($game->swingRequestArrayArray[0]['X'][0] instanceof BMDieSwing);
        $this->assertTrue($game->activeDieArrayArray[0][4] ===
                          $game->swingRequestArrayArray[0]['X'][0]);

        $this->assertCount(1, $game->swingRequestArrayArray[1]);
        $this->assertTrue(array_key_exists('X', $game->swingRequestArrayArray[1]));
        $this->assertCount(2, $game->swingRequestArrayArray[1]['X']);
        $this->assertTrue($game->swingRequestArrayArray[1]['X'][0] instanceof BMDieSwing);
        $this->assertTrue($game->swingRequestArrayArray[1]['X'][1] instanceof BMDieSwing);
        $this->assertTrue($game->activeDieArrayArray[1][3] ===
                          $game->swingRequestArrayArray[1]['X'][0]);
        $this->assertTrue($game->activeDieArrayArray[1][4] ===
                          $game->swingRequestArrayArray[1]['X'][1]);

        $this->assertTrue(isset($game->swingValueArrayArray));
        $this->assertEquals(array(array('X' => NULL), array('X' => NULL)),
                            $game->swingValueArrayArray);
        $this->assertFalse($game->allValuesSpecified);

        // check round info
        $this->assertEquals(1, $game->roundNumber);
        $this->assertEquals(4, $game->maxWins);

        // check action info
        $this->assertFalse(isset($game->attack));
        $this->assertEquals(0, $game->nRecentPasses);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);

        // check score
        $this->assertFalse(isset($game->roundScoreArray));
        $this->assertCount(2, $game->gameScoreArrayArray);
        $this->assertEquals(0, $game->gameScoreArrayArray[0]['W']);
        $this->assertEquals(0, $game->gameScoreArrayArray[0]['L']);
        $this->assertEquals(0, $game->gameScoreArrayArray[0]['D']);
        $this->assertEquals(0, $game->gameScoreArrayArray[1]['W']);
        $this->assertEquals(0, $game->gameScoreArrayArray[1]['L']);
        $this->assertEquals(0, $game->gameScoreArrayArray[1]['D']);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::create_game
     */
    public function test_create_self_game() {
        // attempt to create a game with the same player on both sides
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId1WithoutAutopass),
                                             array('Bauer', 'Stark'), 4);
        $this->assertNull($retval);
        $this->assertEquals('Game create failed because a player has been selected more than once.',
                            $this->object->message);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::create_game
     */
    public function test_create_game_with_invalid_parameters() {
        // attempt to create a game with a non-integer number of max wins
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Bauer', 'Stark'), 4.5);
        $this->assertNull($retval);
        $this->assertEquals('Game create failed because the maximum number of wins was invalid.',
                            $this->object->message);

        // attempt to create a game with a zero number of max wins
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Bauer', 'Stark'), 0);
        $this->assertNull($retval);
        $this->assertEquals('Game create failed because the maximum number of wins was invalid.',
                            $this->object->message);

        // attempt to create a game with a large number of max wins
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Bauer', 'Stark'), 6);
        $this->assertNull($retval);
        $this->assertEquals('Game create failed because the maximum number of wins was invalid.',
                            $this->object->message);

        // attempt to create a game with an invalid button name
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('KJQOERUCHC', 'Stark'), 3);
        $this->assertNull($retval);
        $this->assertEquals('Game create failed because a button name was not valid.',
                            $this->object->message);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_load_game_after_setting_swing_values() {
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Bauer', 'Stark'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);
        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);
        // specify swing dice correctly
        $game->swingValueArrayArray = array(array('X'=>19), array('X'=>5));
        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // check player info
        $this->assertCount(2, $game->playerIdArray);
        $this->assertEquals(2, $game->nPlayers);
        $this->assertEquals(self::$userId1WithoutAutopass, $game->playerIdArray[0]);
        $this->assertEquals(self::$userId2WithoutAutopass, $game->playerIdArray[1]);
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertTrue(isset($game->activePlayerIdx));
        $this->assertTrue(isset($game->playerWithInitiativeIdx));
        $this->assertFalse(isset($game->attackerPlayerIdx));
        $this->assertFalse(isset($game->defenderPlayerIdx));
        $this->assertEquals(array(FALSE, FALSE), $game->isPrevRoundWinnerArray);

        // check buttons
        $this->assertCount(2, $game->buttonArray);
        $this->assertTrue(is_a($game->buttonArray[0], 'BMButton'));
        $this->assertEquals('Bauer', $game->buttonArray[0]->name);
        $this->assertEquals('(8) (10) (12) (20) (X)', $game->buttonArray[0]->recipe);

        $this->assertTrue(is_a($game->buttonArray[1], 'BMButton'));
        $this->assertEquals('Stark', $game->buttonArray[1]->name);
        $this->assertEquals('(4) (6) (8) (X) (X)', $game->buttonArray[1]->recipe);

        // check dice
        $this->assertTrue(isset($game->activeDieArrayArray));
        $this->assertCount(2, $game->activeDieArrayArray);

        $expectedRecipes = array(array('(8)', '(10)', '(12)', '(20)', '(X)'),
                                 array('(4)', '(6)', '(8)', '(X)', '(X)'));
        $expectedSizes = array(array(8, 10, 12, 20, 19),
                               array(4, 6, 8, 5, 5));

        foreach ($game->activeDieArrayArray as $playerIdx => $activeDieArray) {
            $this->assertEquals(count($expectedRecipes[$playerIdx]),
                                count($activeDieArray));
            for ($dieIdx = 0; $dieIdx <= 4; $dieIdx++) {
                $this->assertEquals($expectedRecipes[$playerIdx][$dieIdx],
                                    $activeDieArray[$dieIdx]->recipe);
                $this->assertEquals($game, $activeDieArray[$dieIdx]->ownerObject);
                if (is_nan($expectedSizes[$playerIdx][$dieIdx])) {
                    $this->assertFalse(isset($activeDieArray[$dieIdx]->max));
                    $this->assertFalse(isset($activeDieArray[$dieIdx]->value));
                } else {
                    $this->assertEquals($expectedSizes[$playerIdx][$dieIdx],
                                        $activeDieArray[$dieIdx]->max);
                    $this->assertTrue(isset($activeDieArray[$dieIdx]->value));
                }
            }
        }

        $this->assertFalse(isset($game->attackerAllDieArray));
        $this->assertFalse(isset($game->defenderAllDieArray));
        $this->assertFalse(isset($game->attackerAttackDieArray));
        $this->assertFalse(isset($game->attackerAttackDieArray));
        $this->assertFalse(isset($game->auxiliaryDieDecisionArrayArray));
        $this->assertTrue(isset($game->capturedDieArrayArray));
        $this->assertEquals(array(array(), array()), $game->capturedDieArrayArray);

        // check swing details
        $this->assertTrue(isset($game->swingRequestArrayArray));
        $this->assertCount(2, $game->swingRequestArrayArray);
        $this->assertCount(1, $game->swingRequestArrayArray[0]);
        $this->assertTrue(array_key_exists('X', $game->swingRequestArrayArray[0]));
        $this->assertCount(1, $game->swingRequestArrayArray[0]['X']);
        $this->assertTrue($game->swingRequestArrayArray[0]['X'][0] instanceof BMDieSwing);
        $this->assertTrue($game->activeDieArrayArray[0][4] ===
                          $game->swingRequestArrayArray[0]['X'][0]);

        $this->assertCount(1, $game->swingRequestArrayArray[1]);
        $this->assertTrue(array_key_exists('X', $game->swingRequestArrayArray[1]));
        $this->assertCount(2, $game->swingRequestArrayArray[1]['X']);
        $this->assertTrue($game->swingRequestArrayArray[1]['X'][0] instanceof BMDieSwing);
        $this->assertTrue($game->swingRequestArrayArray[1]['X'][1] instanceof BMDieSwing);
        $this->assertTrue($game->activeDieArrayArray[1][3] ===
                          $game->swingRequestArrayArray[1]['X'][0]);
        $this->assertTrue($game->activeDieArrayArray[1][4] ===
                          $game->swingRequestArrayArray[1]['X'][1]);

        $this->assertTrue(isset($game->swingValueArrayArray));
        $this->assertEquals(array(array('X' => 19), array('X' => 5)),
                            $game->swingValueArrayArray);
        $this->assertFalse($game->allValuesSpecified);

        // check round info
        $this->assertEquals(1, $game->roundNumber);
        $this->assertEquals(4, $game->maxWins);

        // check action info
        $this->assertFalse(isset($game->attack));
        $this->assertEquals(0, $game->nRecentPasses);
        $this->assertEquals(TRUE, $game->waitingOnActionArray[$game->activePlayerIdx]);


        // check score
        $this->assertFalse(isset($game->roundScoreArray));
        $this->assertCount(2, $game->gameScoreArrayArray);
        $this->assertEquals(0, $game->gameScoreArrayArray[0]['W']);
        $this->assertEquals(0, $game->gameScoreArrayArray[0]['L']);
        $this->assertEquals(0, $game->gameScoreArrayArray[0]['D']);
        $this->assertEquals(0, $game->gameScoreArrayArray[1]['W']);
        $this->assertEquals(0, $game->gameScoreArrayArray[1]['L']);
        $this->assertEquals(0, $game->gameScoreArrayArray[1]['D']);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_play_turn() {
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Bauer', 'Stark'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);
        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);

        // specify swing dice correctly
        $game->swingValueArrayArray = array(array('X'=>17), array('X'=>8));
        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 8;
        $dieArrayArray[0][1]->value = 1;
        $dieArrayArray[0][2]->value = 10;
        $dieArrayArray[0][3]->value = 15;
        $dieArrayArray[0][4]->value = 7;
        $dieArrayArray[1][0]->value = 2;
        $dieArrayArray[1][1]->value = 3;
        $dieArrayArray[1][2]->value = 8;
        $dieArrayArray[1][3]->value = 4;
        $dieArrayArray[1][4]->value = 1;

        $game->activePlayerIdx = 1;

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $game->attack = array(1,        // attackerPlayerIdx
                              0,        // defenderPlayerIdx
                              array(2), // attackerAttackDieIdxArray
                              array(1), // defenderAttackDieIdxArray
                              'Power'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertCount(4, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);
        $this->assertCount(0, $game->capturedDieArrayArray[0]);
        $this->assertCount(1, $game->capturedDieArrayArray[1]);
        $this->assertEquals(10, $game->capturedDieArrayArray[1][0]->max);
        $this->assertEquals(1, $game->capturedDieArrayArray[1][0]->value);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::load_game
     */
    public function test_load_poison() {
        // Coil: p4 12 p20 20 V
        // Bane: p2 p4 12 12 V
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Coil', 'Bane'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);
        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);

        // specify swing dice correctly
        $game->swingValueArrayArray = array(array('V'=>11), array('V'=>7));
        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 4;
        $dieArrayArray[0][1]->value = 3;
        $dieArrayArray[0][2]->value = 2;
        $dieArrayArray[0][3]->value = 1;
        $dieArrayArray[0][4]->value = 7;
        $dieArrayArray[1][0]->value = 2;
        $dieArrayArray[1][1]->value = 2;
        $dieArrayArray[1][2]->value = 3;
        $dieArrayArray[1][3]->value = 4;
        $dieArrayArray[1][4]->value = 5;

        $game->activePlayerIdx = 0;

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $this->assertEquals(array(-2.5, 9.5), $game->roundScoreArray);

        $game->attack = array(0,        // attackerPlayerIdx
                              1,        // defenderPlayerIdx
                              array(0), // attackerAttackDieIdxArray
                              array(0), // defenderAttackDieIdxArray
                              'Power'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(4, $game->activeDieArrayArray[1]);
        $this->assertCount(1, $game->capturedDieArrayArray[0]);
        $this->assertCount(0, $game->capturedDieArrayArray[1]);
        $this->assertEquals(2, $game->capturedDieArrayArray[0][0]->max);
        $this->assertEquals(2, $game->capturedDieArrayArray[0][0]->value);
        $this->assertEquals(array(-3.5, 11.5), $game->roundScoreArray);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::save_game
     */
    public function test_swing_value_reset_at_end_of_round() {
        // create a dummy game that will be overwritten
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Tess', 'Coil'), 4);
        $gameId = $retval['gameId'];

        // start as if we were close to the end of Round 1

        // load buttons
        $button1 = new BMButton;
        $button1->load('(1) (X)', 'Tess');
        $this->assertEquals('(1) (X)', $button1->recipe);
        // check dice in $button1->dieArray are correct
        $this->assertCount(2, $button1->dieArray);
        $this->assertEquals(1, $button1->dieArray[0]->max);
        $this->assertFalse(isset($button1->dieArray[1]->max));
        $this->assertTrue($button1->dieArray[1] instanceof BMDieSwing);
        $this->assertTrue($button1->dieArray[1]->needsSwingValue);

        $button2 = new BMButton;
        $button2->load('(2) p(V)', 'Coil');
        $this->assertEquals('(2) p(V)', $button2->recipe);
        // check dice in $button2->dieArray are correct
        $this->assertCount(2, $button2->dieArray);
        $this->assertEquals(2, $button2->dieArray[0]->max);
        $this->assertFalse(isset($button2->dieArray[1]->max));
        $this->assertTrue($button2->dieArray[1] instanceof BMDieSwing);
        $this->assertTrue($button2->dieArray[1]->needsSwingValue);
        $this->assertEquals(array('score_value'),
                            array_keys($button2->dieArray[1]->hookList));
        $this->assertEquals(array('BMSkillPoison'),
                            $button2->dieArray[1]->hookList['score_value']);

        // load game
        $game = new BMGame($gameId, array(self::$userId1WithoutAutopass,
                                          self::$userId2WithoutAutopass),
                           array('', ''), 2);
        $this->assertEquals(BMGameState::START_GAME, $game->gameState);
        $this->assertEquals(2, $game->maxWins);
        $game->buttonArray = array($button1, $button2);
        $this->assertEquals($game, $game->buttonArray[0]->ownerObject);
        $this->assertEquals($game, $game->buttonArray[1]->ownerObject);
        $this->assertEquals($game, $game->buttonArray[0]->dieArray[0]->ownerObject);
        $this->assertEquals($game, $game->buttonArray[0]->dieArray[1]->ownerObject);
        $this->assertEquals($game, $game->buttonArray[1]->dieArray[0]->ownerObject);
        $this->assertEquals($game, $game->buttonArray[1]->dieArray[1]->ownerObject);

        $game->waitingOnActionArray = array(FALSE, FALSE);
        $game->proceed_to_next_user_action();
        $this->assertEquals(array(array(), array()), $game->capturedDieArrayArray);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);
        $this->assertEquals(array(array('X' => NULL), array('V' => NULL)),
                            $game->swingValueArrayArray);

        // specify swing dice correctly
        $game->swingValueArrayArray = array(array('X' => 7), array('V' => 11));
        $game->proceed_to_next_user_action();
        $this->assertTrue($game->activeDieArrayArray[0][1] instanceof BMDieSwing);
        $this->assertTrue($game->activeDieArrayArray[1][1] instanceof BMDieSwing);
        $this->assertFalse($game->activeDieArrayArray[0][1]->needsSwingValue);
        $this->assertFalse($game->activeDieArrayArray[1][1]->needsSwingValue);

        $this->assertEquals(1, array_sum($game->waitingOnActionArray));
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(array(array('X' => 7), array('V' => 11)),
                            $game->swingValueArrayArray);
        $this->assertEquals(7,  $game->activeDieArrayArray[0][1]->max);
        $this->assertEquals(11, $game->activeDieArrayArray[1][1]->max);

        $this->assertNotNull($game->activeDieArrayArray[0][1]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][1]->value);

        $this->assertEquals(array('score_value'),
                            array_keys($game->activeDieArrayArray[1][1]->hookList));
        $this->assertEquals(array('BMSkillPoison'),
                            $game->activeDieArrayArray[1][1]->hookList['score_value']);

        $this->assertEquals(array(4, -10), $game->roundScoreArray);

        // artificially set player 1 as winning initiative
        $game->playerWithInitiativeIdx = 0;
        $game->activePlayerIdx = 0;
        $game->waitingOnActionArray = array(TRUE, FALSE);
        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 1;
        $dieArrayArray[0][1]->value = 1;
        $dieArrayArray[1][0]->value = 1;
        $dieArrayArray[1][1]->value = 1;

        // perform attack
        $game->attack = array(0,        // attackerPlayerIdx
                              1,        // defenderPlayerIdx
                              array(0), // attackerAttackDieIdxArray
                              array(1), // defenderAttackDieIdxArray
                              'Power'); // attackType

        $this->assertEquals(array('X'), array_keys($game->swingValueArrayArray[0]));
        $this->assertEquals(7, $game->swingValueArrayArray[0]['X']);
        $this->assertEquals(array('V'), array_keys($game->swingValueArrayArray[1]));
        $this->assertEquals(11, $game->swingValueArrayArray[1]['V']);

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $this->assertEquals(array('X'), array_keys($game->swingValueArrayArray[0]));
        $this->assertEquals(7, $game->swingValueArrayArray[0]['X']);
        $this->assertEquals(array('V'), array_keys($game->swingValueArrayArray[1]));
        $this->assertEquals(11, $game->swingValueArrayArray[1]['V']);

        $this->assertEquals(1, count($game->activeDieArrayArray[1]));

        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 1;

        // perform attack
        $game->attack = array(1,        // attackerPlayerIdx
                              0,        // defenderPlayerIdx
                              array(0), // attackerAttackDieIdxArray
                              array(1), // defenderAttackDieIdxArray
                              'Power'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[1][0]->value = 1;

        // perform attack
        $game->attack = array(0,        // attackerPlayerIdx
                              1,        // defenderPlayerIdx
                              array(0), // attackerAttackDieIdxArray
                              array(0), // defenderAttackDieIdxArray
                              'Power'); // attackType

        $this->assertEquals(array('X'), array_keys($game->swingValueArrayArray[0]));
        $this->assertEquals(7, $game->swingValueArrayArray[0]['X']);
        $this->assertEquals(array('V'), array_keys($game->swingValueArrayArray[1]));
        $this->assertEquals(11, $game->swingValueArrayArray[1]['V']);

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $this->assertEquals(array(array('W' => 0, 'L' => 1, 'D' => 0),
                                  array('W' => 1, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);

        $this->assertEquals(array('X'), array_keys($game->swingValueArrayArray[0]));
        $this->assertFalse(isset($game->swingValueArrayArray[0]['X']));
        $this->assertEquals(array('V'), array_keys($game->swingValueArrayArray[1]));
        $this->assertTrue(isset($game->swingValueArrayArray[1]['V']));
        $this->assertTrue(isset($game->activeDieArrayArray[1][4]->swingValue));
        $this->assertEquals(array(TRUE, FALSE), $game->waitingOnActionArray);
    }

    /**
     * @depends test_create_user
     *
     * @covers BMInterface::save_game
     */
    public function test_swing_value_reset_at_end_of_game() {
        // create a dummy game that will be overwritten
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Tess', 'Coil'), 1);
        $gameId = $retval['gameId'];

        // start as if we were close to the end of the game
        // load buttons
        $button1 = new BMButton;
        $button1->load('(X)', 'Test1');

        $button2 = new BMButton;
        $button2->load('(V)', 'Test2');

        // load game
        $game = new BMGame($gameId, array(self::$userId1WithoutAutopass,
                                          self::$userId2WithoutAutopass),
                           array('', ''), 1);
        $game->buttonArray = array($button1, $button2);

        $game->waitingOnActionArray = array(FALSE, FALSE);

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // specify swing dice correctly
        $game->swingValueArrayArray = array(array('X' => 7), array('V' => 11));
        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // artificially set player 1 as winning initiative
        $game->playerWithInitiativeIdx = 0;

        // artificially set player 2 as being active
        $game->activePlayerIdx = 1;
        $game->waitingOnActionArray = array(FALSE, TRUE);
        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;

        $dieArrayArray[0][0]->value = 1;
        $dieArrayArray[1][0]->value = 2;

        // perform attack
        $game->attack = array(1,        // attackerPlayerIdx
                              0,        // defenderPlayerIdx
                              array(0), // attackerAttackDieIdxArray
                              array(0), // defenderAttackDieIdxArray
                              'Power'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::END_GAME, $game->gameState);
        $this->assertEquals(array(array(), array()), $game->swingValueArrayArray);
        $this->assertEquals(array(array('W' => 0, 'L' => 1, 'D' => 0),
                                  array('W' => 1, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertEquals(1, $game->roundNumber);
    }


    /**
     * The following unit tests ensure that the swing values are persistent,
     * even when the swing dice have been changed to normal dice,
     *   e.g., by a berserk attack.
     *
     * @depends test_create_user
     *
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_swing_value_persistence() {
        // create a dummy game that will be overwritten
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Tess', 'Coil'), 4);
        $gameId = $retval['gameId'];

        // start as if we were close to the end of Round 1

        // load buttons
        $button1 = new BMButton;
        $button1->load('(1) (X)', 'Test1');
        $this->assertFalse(isset($button1->dieArray[1]->max));
        $this->assertTrue($button1->dieArray[1] instanceof BMDieSwing);
        $this->assertTrue($button1->dieArray[1]->needsSwingValue);

        $button2 = new BMButton;
        $button2->load('(2) p(V)', 'Test2');
        $this->assertEquals('(2) p(V)', $button2->recipe);
        $this->assertFalse(isset($button2->dieArray[1]->max));
        $this->assertTrue($button2->dieArray[1] instanceof BMDieSwing);
        $this->assertTrue($button2->dieArray[1]->needsSwingValue);

        // load game
        $game = new BMGame($gameId, array(self::$userId1WithoutAutopass,
                                          self::$userId2WithoutAutopass),
                           array('', ''), 2);
        $this->assertEquals(BMGameState::START_GAME, $game->gameState);
        $this->assertEquals(2, $game->maxWins);
        $game->buttonArray = array($button1, $button2);
        $game->waitingOnActionArray = array(FALSE, FALSE);
        $game->proceed_to_next_user_action();

        // specify swing dice correctly
        $game->swingValueArrayArray = array(array('X' => 7), array('V' => 11));
        $game->proceed_to_next_user_action();
        $this->assertTrue($game->activeDieArrayArray[0][1] instanceof BMDieSwing);
        $this->assertTrue($game->activeDieArrayArray[1][1] instanceof BMDieSwing);
        $this->assertFalse($game->activeDieArrayArray[0][1]->needsSwingValue);
        $this->assertFalse($game->activeDieArrayArray[1][1]->needsSwingValue);

        $this->assertEquals(1, array_sum($game->waitingOnActionArray));
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(array(array('X' => 7), array('V' => 11)),
                            $game->swingValueArrayArray);
        $this->assertEquals(7,  $game->activeDieArrayArray[0][1]->max);
        $this->assertEquals(11, $game->activeDieArrayArray[1][1]->max);
        $this->assertNotNull($game->activeDieArrayArray[0][1]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][1]->value);

        $newDie = new BMDie;
        $newDie->init(4);
        $newDie->ownerObject = $game->activeDieArrayArray[0][1]->ownerObject;
        $newDie->playerIdx = $game->activeDieArrayArray[0][1]->playerIdx;
        $newDie->originalPlayerIdx = $game->activeDieArrayArray[0][1]->originalPlayerIdx;

        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][1] = $newDie;
        $game->activeDieArrayArray = $dieArrayArray;

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(array(array('X' => 7), array('V' => 11)),
                            $game->swingValueArrayArray);
    }

    /**
     * The following unit tests ensure that the number of passes is updated
     * correctly.
     *
     * @depends test_create_user
     *
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_all_pass() {
        // create a dummy game that will be overwritten
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Wiseman', 'Wiseman'), 4);
        $gameId = $retval['gameId'];

        // load buttons
        $button1 = new BMButton;
        $button1->load('(1) (1)', 'Test1');

        $button2 = new BMButton;
        $button2->load('s(20) s(20)', 'Test2');

        // load game
        $game = new BMGame($gameId, array(self::$userId1WithoutAutopass,
                                          self::$userId2WithoutAutopass),
                           array('', ''), 2);
        $game->buttonArray = array($button1, $button2);

        $game->waitingOnActionArray = array(FALSE, FALSE);
        $game->proceed_to_next_user_action();

        $this->assertCount(2, $game->activeDieArrayArray[0]);
        $this->assertCount(2, $game->activeDieArrayArray[1]);

        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 1;
        $dieArrayArray[0][1]->value = 1;
        $dieArrayArray[1][0]->value = 20;
        $dieArrayArray[1][1]->value = 20;

        // artificially guarantee that the active player is player 1
        $game->activePlayerIdx = 0;
        $game->waitingOnActionArray = array(TRUE, FALSE);

        // player 1 passes
        $game->attack = array(0, 1, array(), array(), 'Pass');
        $game->proceed_to_next_user_action();

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(1, $game->activePlayerIdx);
        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(array(array('W' => 0, 'L' => 0, 'D' => 0),
                                  array('W' => 0, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertEquals(1, $game->nRecentPasses);

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(1, $game->activePlayerIdx);
        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(array(array('W' => 0, 'L' => 0, 'D' => 0),
                                  array('W' => 0, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertEquals(1, $game->nRecentPasses);
        $this->assertCount(2, $game->activeDieArrayArray[0]);
        $this->assertCount(2, $game->activeDieArrayArray[1]);

        // player 2 passes
        $game->attack = array(1, 0, array(), array(), 'Pass');
        $game->proceed_to_next_user_action();

        // beginning of round 2, active dice reloaded from Wiseman
        $this->assertEquals(array(array('W' => 0, 'L' => 1, 'D' => 0),
                                  array('W' => 1, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertEquals(0, $game->nRecentPasses);
        $this->assertCount(4, $game->activeDieArrayArray[0]);
        $this->assertCount(4, $game->activeDieArrayArray[1]);
    }

    /**
     * The following unit tests ensure that autopass works correctly.
     *
     * @depends test_create_user
     *
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_autopass() {
        // create a dummy game that will be overwritten
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId3WithAutopass),
                                                   array('Bunnies', 'Peace'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        $this->assertEquals('(1) (1) (1) (1) (X)', $game->buttonArray[0]->recipe);
        $this->assertEquals('s(10) s(12) s(20) s(X) s(X)', $game->buttonArray[1]->recipe);

        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);

        $game->swingValueArrayArray = array(array('X' => 4), array('X' => 20));
        $game->proceed_to_next_user_action();

        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 1;
        $dieArrayArray[0][1]->value = 1;
        $dieArrayArray[0][2]->value = 1;
        $dieArrayArray[0][3]->value = 1;
        $dieArrayArray[0][4]->value = 4;
        $dieArrayArray[1][0]->value = 5;
        $dieArrayArray[1][1]->value = 12;
        $dieArrayArray[1][2]->value = 20;
        $dieArrayArray[1][3]->value = 20;
        $dieArrayArray[1][4]->value = 20;

        // artificially guarantee that the active player is player 1
        $game->activePlayerIdx = 0;
        $game->waitingOnActionArray = array(TRUE, FALSE);

        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // player 1 performs skill attack, player 2 autopasses
        $game->attack = array(0, 1, array(0, 4), array(0), 'Skill');
        $game->proceed_to_next_user_action();
        $this->assertCount(4, $game->activeDieArrayArray[1]);
        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(0, $game->activePlayerIdx);
        $this->assertEquals(array(TRUE, FALSE), $game->waitingOnActionArray);
        $this->assertCount(4, $game->activeDieArrayArray[1]);
        $this->assertCount(1, $game->capturedDieArrayArray[0]);

        // player 1 passes
        $game->attack = array(0, 1, array(), array(), 'Pass');
        $game->proceed_to_next_user_action();
        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);
        $game->swingValueArrayArray = array(array('X' => 4), array('X' => 20));
        $this->object->save_game($game);
        $game = $this->object->load_game($gameId);

        // should now be at the beginning of round 2
        $this->assertEquals(array(array('W' => 0, 'L' => 1, 'D' => 0),
                                  array('W' => 1, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);
    }

    /**
     * The following unit tests ensure that twin dice work correctly.
     *
     * @covers BMInterface::create_game
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    function test_twin_die() {
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Cthulhu', 'Bill'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        // load game
        $this->assertEquals(array(array(), array()), $game->capturedDieArrayArray);
        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);
        $this->assertEquals(array(array(), array('V' => NULL)),
                            $game->swingValueArrayArray);

        // specify swing dice correctly
        $game->swingValueArrayArray = array(array(), array('V' => 11));
        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertTrue($game->activeDieArrayArray[1][3]->dice[0] instanceof BMDieSwing);
        $this->assertFalse($game->activeDieArrayArray[1][3]->dice[0]->needsSwingValue);
        $this->assertTrue($game->activeDieArrayArray[1][3]->dice[1] instanceof BMDieSwing);
        $this->assertFalse($game->activeDieArrayArray[1][3]->dice[1]->needsSwingValue);

        $this->assertEquals(1, array_sum($game->waitingOnActionArray));
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(array(array(), array('V' => 11)),
                            $game->swingValueArrayArray);
        $this->assertEquals( 1, $game->activeDieArrayArray[0][0]->min);
        $this->assertEquals( 1, $game->activeDieArrayArray[0][1]->min);
        $this->assertEquals( 2, $game->activeDieArrayArray[0][2]->min);
        $this->assertEquals( 2, $game->activeDieArrayArray[0][3]->min);
        $this->assertEquals( 2, $game->activeDieArrayArray[0][4]->min);
        $this->assertEquals( 1, $game->activeDieArrayArray[1][0]->min);
        $this->assertEquals( 1, $game->activeDieArrayArray[1][1]->min);
        $this->assertEquals( 1, $game->activeDieArrayArray[1][2]->min);
        $this->assertEquals( 2, $game->activeDieArrayArray[1][3]->min);
        $this->assertEquals( 4, $game->activeDieArrayArray[0][0]->max);
        $this->assertEquals(20, $game->activeDieArrayArray[0][1]->max);
        $this->assertEquals(12, $game->activeDieArrayArray[0][2]->max);
        $this->assertEquals(18, $game->activeDieArrayArray[0][3]->max);
        $this->assertEquals(26, $game->activeDieArrayArray[0][4]->max);
        $this->assertEquals(20, $game->activeDieArrayArray[1][0]->max);
        $this->assertEquals(20, $game->activeDieArrayArray[1][1]->max);
        $this->assertEquals(20, $game->activeDieArrayArray[1][2]->max);
        $this->assertEquals(22, $game->activeDieArrayArray[1][3]->max);

        $this->assertNotNull($game->activeDieArrayArray[0][0]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][1]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][2]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][3]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][4]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][0]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][1]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][2]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][3]->value);

        // artificially set player 1 as winning initiative
        $game->playerWithInitiativeIdx = 0;
        $game->activePlayerIdx = 0;
        $game->waitingOnActionArray = array(TRUE, FALSE);
        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 1;
        $dieArrayArray[0][1]->value = 2;
        $dieArrayArray[0][2]->value = 3;
        $dieArrayArray[0][3]->value = 13;
        $dieArrayArray[0][4]->value = 13;
        $dieArrayArray[1][0]->value = 4;
        $dieArrayArray[1][1]->value = 12;
        $dieArrayArray[1][2]->value = 5;
        $dieArrayArray[1][3]->value = 6;

        // perform valid attack
        $game->attack = array(0,        // attackerPlayerIdx
                              1,        // defenderPlayerIdx
                              array(2), // attackerAttackDieIdxArray
                              array(3), // defenderAttackDieIdxArray
                              'Shadow'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(3, $game->activeDieArrayArray[1]);
        $this->assertCount(1, $game->capturedDieArrayArray[0]);
        $this->assertCount(0, $game->capturedDieArrayArray[1]);
        $this->assertEquals(22, $game->capturedDieArrayArray[0][0]->max);
        $this->assertEquals(6, $game->capturedDieArrayArray[0][0]->value);
    }

    /**
     * The following unit tests ensure that konstant works correctly.
     *
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    function test_konstant() {
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Al-Khwarizmi',
                                                         'Carl Friedrich Gauss'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        // load game
        $this->assertEquals(array(array(), array()), $game->capturedDieArrayArray);
        $this->assertEquals(1, array_sum($game->waitingOnActionArray));
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals( 4, $game->activeDieArrayArray[0][0]->max);
        $this->assertEquals( 6, $game->activeDieArrayArray[0][1]->max);
        $this->assertEquals( 8, $game->activeDieArrayArray[0][2]->max);
        $this->assertEquals(12, $game->activeDieArrayArray[0][3]->max);
        $this->assertEquals(20, $game->activeDieArrayArray[0][4]->max);
        $this->assertEquals( 6, $game->activeDieArrayArray[1][0]->max);
        $this->assertEquals( 8, $game->activeDieArrayArray[1][1]->max);
        $this->assertEquals( 8, $game->activeDieArrayArray[1][2]->max);
        $this->assertEquals(24, $game->activeDieArrayArray[1][3]->max);
        $this->assertEquals(20, $game->activeDieArrayArray[1][4]->max);
        $this->assertTrue($game->activeDieArrayArray[0][1]->has_skill('Konstant'));
        $this->assertFalse($game->activeDieArrayArray[0][1]->doesReroll);
        $this->assertTrue($game->activeDieArrayArray[1][0]->has_skill('Konstant'));
        $this->assertFalse($game->activeDieArrayArray[1][0]->doesReroll);

        $this->assertNotNull($game->activeDieArrayArray[0][0]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][1]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][2]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][3]->value);
        $this->assertNotNull($game->activeDieArrayArray[0][4]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][0]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][1]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][2]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][3]->value);
        $this->assertNotNull($game->activeDieArrayArray[1][4]->value);

        // artificially set player 1 as winning initiative
        $game->playerWithInitiativeIdx = 0;
        $game->activePlayerIdx = 0;
        $game->waitingOnActionArray = array(TRUE, FALSE);
        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 1;
        $dieArrayArray[0][1]->value = 1;
        $dieArrayArray[0][2]->value = 1;
        $dieArrayArray[0][3]->value = 1;
        $dieArrayArray[0][4]->value = 1;
        $dieArrayArray[1][0]->value = 2;
        $dieArrayArray[1][1]->value = 2;
        $dieArrayArray[1][2]->value = 2;
        $dieArrayArray[1][3]->value = 2;
        $dieArrayArray[1][4]->value = 2;

        // perform valid attack
        $game->attack = array(0,        // attackerPlayerIdx
                              1,        // defenderPlayerIdx
                              array(0, 1), // attackerAttackDieIdxArray
                              array(0), // defenderAttackDieIdxArray
                              'Skill'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(4, $game->activeDieArrayArray[1]);
        $this->assertCount(1, $game->capturedDieArrayArray[0]);
        $this->assertCount(0, $game->capturedDieArrayArray[1]);
        $this->assertEquals(6, $game->capturedDieArrayArray[0][0]->max);
        $this->assertEquals(2, $game->capturedDieArrayArray[0][0]->value);

        // check explicitly that the konstant die does not reroll
        $this->assertEquals(1, $game->activeDieArrayArray[0][1]->value);
        $this->assertFalse($game->activeDieArrayArray[0][1]->doesReroll);
    }

    /**
     * The following unit tests ensure that surrender attacks work correctly.
     *
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_surrender() {
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Sonia', 'Tamiya'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        $game->playerWithInitiativeIdx = 1;
        $game->activePlayerIdx = 1;
        $game->waitingOnActionArray = array(FALSE, TRUE);
        // artificially set die values
        $dieArrayArray = $game->activeDieArrayArray;
        $dieArrayArray[0][0]->value = 4;
        $dieArrayArray[0][1]->value = 2;
        $dieArrayArray[0][2]->value = 8;
        $dieArrayArray[0][3]->value = 12;
        $dieArrayArray[0][4]->value = 7;
        $dieArrayArray[1][0]->value = 4;
        $dieArrayArray[1][1]->value = 1;
        $dieArrayArray[1][2]->value = 8;
        $dieArrayArray[1][3]->value = 12;
        $dieArrayArray[1][4]->value = 17;

        // perform invalid surrender attack with dice selected
        $game->attack = array(1,        // attackerPlayerIdx
                              0,        // defenderPlayerIdx
                              array(2), // attackerAttackDieIdxArray
                              array(1), // defenderAttackDieIdxArray
                              'Surrender'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(1, $game->activePlayerIdx);
        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);

        $this->assertEquals(array(array('W' => 0, 'L' => 0, 'D' => 0),
                                  array('W' => 0, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);
        $this->assertCount(0, $game->capturedDieArrayArray[0]);
        $this->assertCount(0, $game->capturedDieArrayArray[1]);

        // perform invalid surrender attack with non-active player
        $game->attack = array(0,        // attackerPlayerIdx
                              1,        // defenderPlayerIdx
                              array(),  // attackerAttackDieIdxArray
                              array(),  // defenderAttackDieIdxArray
                              'Surrender'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(1, $game->activePlayerIdx);
        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertEquals(BMGameState::START_TURN, $game->gameState);

        $this->assertEquals(array(array('W' => 0, 'L' => 0, 'D' => 0),
                                  array('W' => 0, 'L' => 0, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);
        $this->assertCount(0, $game->capturedDieArrayArray[0]);
        $this->assertCount(0, $game->capturedDieArrayArray[1]);

        // perform valid surrender attack
        $game->attack = array(1,        // attackerPlayerIdx
                              0,        // defenderPlayerIdx
                              array(),  // attackerAttackDieIdxArray
                              array(),  // defenderAttackDieIdxArray
                              'Surrender'); // attackType

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);

        $this->assertEquals(array(array('W' => 1, 'L' => 0, 'D' => 0),
                                  array('W' => 0, 'L' => 1, 'D' => 0)),
                            $game->gameScoreArrayArray);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);
        $this->assertCount(0, $game->capturedDieArrayArray[0]);
        $this->assertCount(0, $game->capturedDieArrayArray[1]);
    }

    /**
     * Check that a decline of an auxiliary die works correctly.
     *
     * @covers BMInterface::react_to_auxiliary
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_react_to_auxiliary_both_aux_decline() {
        // Lancelot : (10) (12) (20) (20) (X) +(X)
        // Gawaine  :  (4)  (4) (12) (20) (X) +(6)
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Lancelot', 'Gawaine'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::CHOOSE_AUXILIARY_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(6, $game->activeDieArrayArray[0]);
        $this->assertCount(6, $game->activeDieArrayArray[1]);

        // a non-player attempts an action
        $this->assertFalse(
            $this->object->react_to_auxiliary(
                0,
                $gameId,
                'decline')
        );

        // player 1 attempts an invalid action
        $this->assertFalse(
            $this->object->react_to_auxiliary(
                self::$userId1WithoutAutopass,
                $gameId,
                'rubbish')
        );

        // player 1 declines
        $this->assertTrue(
            $this->object->react_to_auxiliary(
                self::$userId1WithoutAutopass,
                $gameId,
                'decline')
        );
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);
        foreach ($game->activeDieArrayArray as $activeDieArray) {
            foreach ($activeDieArray as $die) {
                $this->assertFalse($die->has_skill('Auxiliary'));
            }
        }
        $this->assertEquals('(10) (12) (20) (20) (X)',
                            $game->buttonArray[0]->recipe);
        $this->assertEquals('(4) (4) (12) (20) (X)',
                            $game->buttonArray[1]->recipe);
    }

    /**
     * Check that courtesy auxiliary dice are given correctly.
     *
     * @covers BMInterface::react_to_auxiliary
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     * @covers BMGame::add_selected_auxiliary_dice
     */
    public function test_react_to_auxiliary_one_aux_decline() {
        // Kublai   :  (4) (8) (12) (20) (X)
        // Gawaine  :  (4) (4) (12) (20) (X) +(6)
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Kublai', 'Gawaine'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::CHOOSE_AUXILIARY_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(6, $game->activeDieArrayArray[0]);
        $this->assertCount(6, $game->activeDieArrayArray[1]);
        $this->assertTrue($game->activeDieArrayArray[0][5]->has_skill('Auxiliary'));

        // player 1 chooses to add auxiliary die
        $this->assertTrue(
            $this->object->react_to_auxiliary(
                self::$userId1WithoutAutopass,
                $gameId,
                'add',
                5
            )
        );

        $game = $this->object->load_game($gameId);
        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(6, $game->activeDieArrayArray[0]);
        $this->assertCount(6, $game->activeDieArrayArray[1]);
        $this->assertTrue($game->activeDieArrayArray[0][5]->has_skill('Auxiliary'));
        $this->assertTrue($game->activeDieArrayArray[0][5]->selected);

        // player 1 tries incorrectly to act again
        $this->assertFalse(
            $this->object->react_to_auxiliary(
                self::$userId1WithoutAutopass,
                $gameId,
                'add',
                5)
        );

        // player 2 declines
        $this->assertTrue(
            $this->object->react_to_auxiliary(
                self::$userId2WithoutAutopass,
                $gameId,
                'decline')
            );
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(5, $game->activeDieArrayArray[1]);
        foreach ($game->activeDieArrayArray as $activeDieArray) {
            foreach ($activeDieArray as $die) {
                $this->assertFalse($die->has_skill('Auxiliary'));
            }
        }
        $this->assertEquals('(4) (8) (12) (20) (X)',
                            $game->buttonArray[0]->recipe);
        $this->assertEquals('(4) (4) (12) (20) (X)',
                            $game->buttonArray[1]->recipe);
    }

    /**
     * Check that courtesy auxiliary dice are given correctly.
     *
     * @covers BMInterface::react_to_auxiliary
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     * @covers BMGame::add_selected_auxiliary_dice
     */
    public function test_react_to_auxiliary_one_aux_accept() {
        // Kublai   :  (4) (8) (12) (20) (X)
        // Gawaine  :  (4) (4) (12) (20) (X) +(6)
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Kublai', 'Gawaine'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::CHOOSE_AUXILIARY_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(6, $game->activeDieArrayArray[0]);
        $this->assertCount(6, $game->activeDieArrayArray[1]);
        $this->assertTrue($game->activeDieArrayArray[0][5]->has_skill('Auxiliary'));

        // player 1 tries incorrectly adding a non-auxiliary die
        $this->assertFalse(
            $this->object->react_to_auxiliary(
                self::$userId1WithoutAutopass,
                $gameId,
                'add',
                0
            )
        );

        // player 1 chooses to add an auxiliary die
        $this->assertTrue(
            $this->object->react_to_auxiliary(
                self::$userId1WithoutAutopass,
                $gameId,
                'add',
                5
            )
        );

        $game = $this->object->load_game($gameId);
        $this->assertEquals(array(FALSE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(6, $game->activeDieArrayArray[0]);
        $this->assertCount(6, $game->activeDieArrayArray[1]);
        $this->assertTrue($game->activeDieArrayArray[0][5]->has_skill('Auxiliary'));
        $this->assertTrue($game->activeDieArrayArray[0][5]->selected);

        $this->assertTrue(
            $this->object->react_to_auxiliary(
                self::$userId2WithoutAutopass,
                $gameId,
                'add',
                5)
            );
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::SPECIFY_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, TRUE), $game->waitingOnActionArray);
        $this->assertCount(6, $game->activeDieArrayArray[0]);
        $this->assertCount(6, $game->activeDieArrayArray[1]);
        foreach ($game->activeDieArrayArray as $activeDieArray) {
            foreach ($activeDieArray as $die) {
                $this->assertFalse($die->has_skill('Auxiliary'));
            }
        }
        $this->assertEquals('(4) (8) (12) (20) (X) (6)',
                            $game->buttonArray[0]->recipe);
        $this->assertEquals('(4) (4) (12) (20) (X) (6)',
                            $game->buttonArray[1]->recipe);
    }

    /**
     * Check that a bad action is handled gracefully.
     *
     * @covers BMInterface::react_to_auxiliary
     */
    public function test_react_to_auxiliary_invalid() {
        $this->assertFalse($this->object->react_to_auxiliary(1.5, 2.5, 'ha!'));
    }

    /**
     * Check that a decline of a reserve die works correctly.
     *
     * @covers BMInterface::react_to_reserve
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_react_to_reserve_decline() {
        // Sailor Moon : (8) (8) (10) (20) r(6) r(10) r(20) r(20)
        // Queen Beryl : (4) (8) (12) (20) r(4) r(12) r(20) r(20)
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Sailor Moon', 'Queen Beryl'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        $game->gameScoreArrayArray = array(array('W' => 0, 'L' => 1, 'D' => 0),
                                           array('W' => 1, 'L' => 0, 'D' => 0));
        $game->isPrevRoundWinnerArray = array(FALSE, TRUE);
        $game->waitingOnActionArray = array(FALSE, FALSE);
        $game->gameState = BMGameState::LOAD_DICE_INTO_BUTTONS;

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(BMGameState::CHOOSE_RESERVE_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, FALSE), $game->waitingOnActionArray);
        $this->assertCount(8, $game->activeDieArrayArray[0]);
        $this->assertCount(8, $game->activeDieArrayArray[1]);

        // a non-player attempts an action
        $this->assertFalse(
            $this->object->react_to_reserve(
                0,
                $gameId,
                'decline')
        );

        // player 1 attempts an invalid action
        $this->assertFalse(
            $this->object->react_to_reserve(
                self::$userId1WithoutAutopass,
                $gameId,
                'rubbish')
        );

        // player 2 attempts a reserve action
        $this->assertFalse(
            $this->object->react_to_reserve(
                self::$userId2WithoutAutopass,
                $gameId,
                'add',
                6)
        );

        // player 1 declines
        $this->assertTrue(
            $this->object->react_to_reserve(
                self::$userId1WithoutAutopass,
                $gameId,
                'decline')
        );
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(1, array_sum($game->waitingOnActionArray));
        $this->assertCount(4, $game->activeDieArrayArray[0]);
        $this->assertCount(4, $game->activeDieArrayArray[1]);
        foreach ($game->activeDieArrayArray as $activeDieArray) {
            foreach ($activeDieArray as $die) {
                $this->assertFalse($die->has_skill('Reserve'));
            }
        }
        $this->assertEquals('(8) (8) (10) (20) r(6) r(10) r(20) r(20)',
                            $game->buttonArray[0]->recipe);
        $this->assertEquals('(4) (8) (12) (20) r(4) r(12) r(20) r(20)',
                            $game->buttonArray[1]->recipe);
    }

    /**
     * Check that a decline of a reserve die works correctly.
     *
     * @covers BMInterface::react_to_reserve
     * @covers BMInterface::save_game
     * @covers BMInterface::load_game
     */
    public function test_react_to_reserve_add() {
        // Sailor Moon : (8) (8) (10) (20) r(6) r(10) r(20) r(20)
        // Queen Beryl : (4) (8) (12) (20) r(4) r(12) r(20) r(20)
        $retval = $this->object->create_game(array(self::$userId1WithoutAutopass,
                                                   self::$userId2WithoutAutopass),
                                                   array('Sailor Moon', 'Queen Beryl'), 4);
        $gameId = $retval['gameId'];
        $game = $this->object->load_game($gameId);

        $game->gameScoreArrayArray = array(array('W' => 0, 'L' => 1, 'D' => 0),
                                           array('W' => 1, 'L' => 0, 'D' => 0));
        $game->isPrevRoundWinnerArray = array(FALSE, TRUE);
        $game->waitingOnActionArray = array(FALSE, FALSE);
        $game->gameState = BMGameState::LOAD_DICE_INTO_BUTTONS;

        $this->object->save_game($game);
        $game = $this->object->load_game($game->gameId);

        $this->assertEquals(BMGameState::CHOOSE_RESERVE_DICE, $game->gameState);
        $this->assertEquals(array(TRUE, FALSE), $game->waitingOnActionArray);
        $this->assertCount(8, $game->activeDieArrayArray[0]);
        $this->assertCount(8, $game->activeDieArrayArray[1]);

        // a non-player attempts an action
        $this->assertFalse(
            $this->object->react_to_reserve(
                0,
                $gameId,
                'add')
        );

        // player 1 adds reserve die
        $this->assertTrue(
            $this->object->react_to_reserve(
                self::$userId1WithoutAutopass,
                $gameId,
                'add',
                5)
        );
        $game = $this->object->load_game($gameId);

        $this->assertEquals(BMGameState::START_TURN, $game->gameState);
        $this->assertEquals(1, array_sum($game->waitingOnActionArray));
        $this->assertCount(5, $game->activeDieArrayArray[0]);
        $this->assertCount(4, $game->activeDieArrayArray[1]);
        foreach ($game->activeDieArrayArray as $activeDieArray) {
            foreach ($activeDieArray as $die) {
                $this->assertFalse($die->has_skill('Reserve'));
            }
        }
        $this->assertEquals(10, $game->activeDieArrayArray[0][4]->max);
        $this->assertEquals('(8) (8) (10) (20) r(6) (10) r(20) r(20)',
                            $game->buttonArray[0]->recipe);
        $this->assertEquals('(4) (8) (12) (20) r(4) r(12) r(20) r(20)',
                            $game->buttonArray[1]->recipe);
    }
}

?>
