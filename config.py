# =============================================== FitBit Synchronization ===============================================
# Change to True to enable weight synchronization with FitBit. Go to http://localhost:80/pair for more info.

# WARNING! You should not expose the default http port (80) of the device you're running this on to the outside of your
# network. FitBit OAuth2 tokens are stored in plain text therefore the security of the tokens directly correlate to the
# security of this project folder.
FITBIT_SYNC_ENABLED = False
# ======================================================================================================================


# ================================================= Weight Fluctuation =================================================
# The following value is used to determine which weight belongs to which user. If the difference between the closest
# weight logged to the current weight logged (when data exists) exceeds this amount, the weight will be assigned to a
# new user. Lower values might cause issues when measuring weight inbetween long periods of time. This system might not
# work for multiple users that weight a very similar amount.
#
# For example:
# - User 1 weights 100 kg and is logged in the data file.
# - User 2 weights 60 kg and is logged in the data file.
#
# - A new weight value is registered of 98.9 kg. Since the smallest difference between weights is 1.1kg (which is
#   within the default allowed weight fluctuation), the new weight is assigned to User 1.
# - A new weight value is registered of 81 kg. Since the difference between last registered user weights
#   (60kg [diff 21 kg] and 98.9 kg [diff 17.9 kg.]) exceeds the default allowed weight fluctuation of 10kg - a new user
#   is created
#
ALLOWED_WEIGHT_FLUCTUATION_KG = 10.0
# ======================================================================================================================


# ======================================================= Other ========================================================
# Various other settings, there should be no reason to change these
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # Sets the date format in which to store the weight
WEIGHT_LOG_LOCATION = "data/weight.csv"  # Sets the weight file location
# ======================================================================================================================
