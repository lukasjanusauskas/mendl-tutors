student_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': [
            'first_name', 
            'last_name', 
            'date_of_birth', 
            'subjects', 
            'class', 
            'password_hashed', 
            'parents_phone_numbers'
        ],
        'properties': {
            'full_name': {
                'bsonType': 'string',
                "minLength": 1, # Reiketu prideti minimalu, negali buti tuscias
                'description': "Student's full name"
            },
            'password_hashed':{
                'bsonType': 'string',
                'minLength': 1,
                'description': "Password SHA-256 encrypted"
            },
            'date_of_birth':{
                'bsonType': 'date',
                # Cia validacija galima bus daryti su paciu API, jei reikes
                'description': "Student's date of birth"
            },
            'class': {
                'bsonType': 'int',
                'minimum': 1,
                'maximum': 12,
                'description': "Student's specified class"
            },
            'subjects': {
                'bsonType': 'array',
                'minItems': 1,
                # Reikes pasakyti, kad nededam galimu reiksmiu saraso, nes gali keistis/daugeti pleciantis
                'items': {
                    'bsonType': 'string',
                    'minLength': 1,
                },
                'description': "List of subjects the student takes"
            },
            'phone_number': {
                'bsonType': 'string',
                'pattern': r'^\+?\d{7,15}$',
                'description': "Student's phone number"
            },
            'parents_phone_numbers':{
                'bsonType': 'array',
                'items': {
                    'bsonType': 'string',
                    'pattern': r'^\+?\d{7,15}$'
                },
                'description': "Parent's phone numbers"
            },
            'student_email': {
                'bsonType': 'string',
                'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                'description': "Student's email"
            },
            'parents_emails': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'string',
                    'pattern': r'^[^@]+@[^@]+\.[^@]+$'
                },
                'description': "Parent's email"
            }
        }
    }
}

tutor_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': [
            'first_name', 
            'last_name', 
            'email', 
            'date_of_birth', 
            'subjects', 
            'subjects_students', 
            'password_hashed'
        ],
        'properties': {
            'first_name': {
                'bsonType': 'string',
                'minLength': 1,
                'description': "Tutor's full name"
            },
            'last_name': {
                'bsonType': 'string',
                'minLength': 1,
                'description': "Tutor's full name"
            },
            'email': {
                'bsonType': 'string',
                'minLength': 1,
                'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                'description': "Tutor's email"
            },
            'date_of_birth':{
                'bsonType': 'date',
                'description': "Tutor's date of birth"
            },
            'subjects': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    # Dėl API paprastumo turi būti max_class, jei naudotojas neįrašo, užpildom su 12
                    'required': ['subject', 'max_class'], 
                    'properties': {
                        'subject': {'bsonType': 'string'},
                        'max_class': {'bsonType': 'int'}
                    }
                }
            },
            'subjects_students': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'required': ['student', 'subject'],
                    'properties': {
                        'student': {
                            'bsonType': 'object',
                            'additionalProperties': True,
                            'required': ['student_id', 'first_name', 'last_name', 'parents_phone_numbers'],
                            'properties': {
                                'student_id': {'bsonType': 'objectId'},
                                'first_name': {
                                    'bsonType': 'string',
                                    "minLength": 1,
                                    'description': "Student's full name"
                                },
                                'last_name': {
                                    'bsonType': 'string',
                                    "minLength": 1,
                                    'description': "Student's full name"
                                },
                                'phone_number': {
                                    'bsonType': 'string',
                                    'pattern': r'^\+?\d{7,15}$',  
                                    'description': "Student's phone number"
                                },
                                'parents_phone_numbers':{
                                    'bsonType': 'array',
                                    'items': {
                                        'bsonType': 'string',
                                        'pattern': r'^\+?\d{7,15}$'
                                    },
                                    'description': "Parent's phone numbers"
                                }
                            }
                        },
                        'subject':{
                            'bsonType': 'string',
                            'description': 'Subject that the student will be taught'
                        }
                    }
                },
                'description': "List of subjects the student takes"
            },
            'phone_number': {
                'bsonType': 'string',
                'pattern': r'^\+?\d{7,15}$',
                'description': "Phone number"
            },
            'password_hashed':{
                'bsonType': 'string',
                'minLength': 1,
                'description': "Password SHA-256 encrypted"
            }
        }
    }
}

lesson_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['time', 'tutor', 'students', 'subject', 'link'],
        'properties': {
            'time': {
                'bsonType': 'date',
                'description': "Lesson date and time"
            },
            'tutor': {
                'bsonType': 'object',
                'required': ['tutor_id', 'first_name', 'last_name'],
                'properties': {
                    'tutor_id': {'bsonType': 'objectId'},
                    'first_name': {
                        'bsonType': 'string',
                        'minLength': 1,
                        'description': "Tutor's full name"
                    },
                    'last_name': {
                        'bsonType': 'string',
                        'minLength': 1,
                        'description': "Tutor's full name"
                    }
                },
                'description': "Tutor's full name"
            },
            'students': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'required': [
                        'student_id', 
                        'student_name', 
                        'parents_phone_number', 
                        'price', 
                        'paid', 
                        'moved'
                    ],
                    'properties': {
                        'student_id': {'bsonType': 'objectId'},
                        'student_name': {
                            'bsonType' : 'string',
                            'minLength': 1,
                            'description': "Student's name"
                        },
                        'parents_phone_number':{
                            'bsonType': 'array',
                            'items': {
                                'bsonType': 'string',
                                'minLength': 1,
                                'pattern': r'^\+?\d{7,15}$',
                            },
                            'description': "Parent's phone number"
                        },
                        'price' :{
                            'bsonType': 'double',
                            'minimum': 0,
                            'maximum': 150,
                            'description': 'Price of the lesson for the student'
                        },
                        'paid':{
                            'bsonType': "bool",
                            'description': "Whether the lesson is paid"
                        },
                        'moved':{
                            'bsonType': "bool",
                            'description': "Whether the lesson is moved"
                        }
                    }
                },
                'description': "List of students attending the lesson"
            },
            'subject': {
                'bsonType': 'string',
                'description': "Subject of the lesson"
            },
            'class': {
                'bsonType': 'int',
                'minimum': 1,
                'maximum': 12,
                'description': "Students specified class"
            },
            'type': {
                'bsonType': 'string',
                'description': "Type of the lesson"
            },
            'link': {
                'bsonType': 'string',
                'description': "Link for the lesson"
            }
        }
    }
}

review_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['time', 'tutor', 'student', 'review_text', 'for_tutor'],
        'properties': {
            'time': {
                'bsonType': 'date',
                'description': "Review date"
            },
            'tutor': {
                'bsonType': 'string',
                'minLength': 1,
                'description': "Tutor's full name"
            },
            'student': {
                'bsonType': 'string',
                'minLength': 1,
                'description': "Student's full name"
            },
            'review_text': {
                'bsonType': 'string',
                'description': 'Text of the review'
            },
            'rating': {
                'bsonType': 'int',
                'minimum': 1,
                'maximum': 5,
                'description': "Rating from 1 to 5"
            },
            'for_tutor': {
                'bsonType': 'bool',
                'description': "Type of review true if for tutor, false if for student"
            }
        }
    }
}