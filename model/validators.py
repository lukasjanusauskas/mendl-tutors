student_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['full_name','dob','subjects', 'class', 'parents_phone_number'],
        'properties': {
            'full_name': {
                'bsonType': 'string',
                "minLength": 1, # Reiketu prideti minimalu, negali buti tuscias
                'description': "Student's full name"
            },
            'dob':{
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
                # Reikes pasakyti, kad nededam galimu reiksmiu saraso, nes gali keistis/daugeti pleciantis
                'items': {
                    'bsonType': 'string'
                },
                'description': "List of subjects the student takes"
            },
            'phone_number': {
                'bsonType': 'string',
                'pattern': r'^\+?\d{7,15}$',  
                'description': "Student's phone number"
            },
            'parents_phone_number':{
                'bsonType': 'string',
                'pattern': r'^\+?\d{7,15}$',  
                'description': "Parent's phone number"
            },
            'student_email': {
                'bsonType': 'string',
                'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                'description': "Student's email"
            },
            'parents_email': {
                'bsonType': 'string',
                'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                'description': "Parent's email"
            }

        }
    }
}

tutor_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['full_name','dob','number_of_lessons','username','password_encrypted','email'],
        'properties': {
            'full_name': {
                'bsonType': 'string',
                'description': "Tutor's full name"
            },
            'dob':{
                'bsonType': 'date',
                'description': "Tutor's date of birth"
            },
            'rating': {
                'bsonType': 'double',
                # 'minimum': 0,
                'minimum': 1, # Zemiau reitingai nuo 1 iki 5, tai ir cia turetu buti, jeigu reitingu nera, tai ir cia nera
                'maximum': 5,
                'description': "Tutor's rating"
            },
            'number_of_lessons': {
                'bsonType': 'int',
                'minimum': 0,
                'description': "Tutor's specified class"
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
                            'required': ['full_name'],
                            'properties': {
                                'full_name': {
                                    'bsonType': 'string',
                                    "minLength": 1, # Reiketu prideti minimalu, negali buti tuscias
                                    'description': "Student's full name"
                                },
                                'phone_number': {
                                    'bsonType': 'string',
                                    'pattern': r'^\+?\d{7,15}$',  
                                    'description': "Student's phone number"
                                },
                                'parents_phone_number':{
                                    'bsonType': 'string',
                                    'pattern': r'^\+?\d{7,15}$',  
                                    'description': "Parent's phone number"
                                },
                                'student_email': {
                                    'bsonType': 'string',
                                    'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                                    'description': "Student's email"
                                },
                                'parents_email': {
                                    'bsonType': 'string',
                                    'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                                    'description': "Parent's email"
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
            'username':{
                'bsonType': 'string', 
                'description': "Username"
            },
            'password_encrypted':{
                'bsonType': 'string', 
                'description': "Username"
            },
            'email': {
                'bsonType': 'string',
                'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                'description': "Tutor's email"
            }
        }
    }
}

lesson_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['time','tutor','students','subject','class','link'],
        'properties': {
            'time': {
                'bsonType': 'date',
                'description': "Lesson date and time"
            },
            'tutor': {
                # Kaip ir 89 eilutej
                'bsonType': 'objectId',
                'description': "Reference to the tutor"
            },
            'students': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'required': ['student','price','paid','moved'],
                    'properties': {
                        'student': {
                            # Kaip ir tas pats
                            'bsonType' : 'objectId',
                            'description': "Reference to the student"
                        },
                        'price' :{
                            'bsonType': 'double',
                            'minimum': 0,
                            'maximum': 150,
                            'description': 'Price of the lesson for the student'
                        },

                        # Gal su tipais padarom enum?

                        'type': {
                            'bsonType': 'string',
                            'enum': ['Moved', 'Unpaid additional', 'Paid additional', 'Unpaid scheduled', 'Paid scheduled']
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

reviews_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['time','tutor','student', 'ratings', 'type'],
        'properties': {
            'time': {
                'bsonType': 'date',
                'description': "Review date"
            },
            'tutor': {
                'bsonType': 'objectId',
                'description': "Reference to the tutor"
            },
            'student': {
                'bsonType': 'objectId',
                'description': "Reference to the student"
            },
            'ratings': {
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
