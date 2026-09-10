# Judge meta-evaluation worksheet

Score each draft 0-10 on each dimension, using the bands below. Write your score in the `human` field of the matching row in the JSONL file next to this one.

Read `docs/05-human-labeling.md` before starting. It defines the closed-book boundary, practice examples and blind workflow.

The judge's own scores are not shown here on purpose: seeing them first would anchor your judgement, and an anchored human column measures nothing.

## commitment groundedness

- **0-2** - The reply promises an outcome, an entitlement or a specific timeframe the email does not support - a claim will be approved, a refund will arrive by a date, a benefit applies.
- **3-5** - The reply introduces a softer commitment the email does not support: an implied service level, an assurance that something will be resolved, a suggestion that a decision is likely.
- **6-8** - The reply commits only to what the email supports, but phrasing in one place could be read as more than the insurer has undertaken.
- **9-10** - Every commitment in the reply is supported by the email or is a generic acknowledgement carrying no deadline or outcome.

## tone match

- **0-3** - The register works against the situation: chatty or padded where the customer faces a deadline, or curt where they are upset or confused.
- **4-6** - Broadly appropriate but uneven - an urgent reply that opens with several lines of sympathy before the action, or a routine reply that reads as a form letter.
- **7-8** - Register fits the situation, with a phrase or two that sits slightly wrong.
- **9-10** - Register fits the situation throughout: urgent handled formally and efficiently, routine handled warmly, neither overdone.

## summary quality

- **0-3** - The summary states something the email does not, or omits the request or the deadline that makes the case what it is.
- **4-6** - Factually contained but the reviewer would still have to read the email to know what to do, or it runs well past two sentences.
- **7-8** - Contained and useful, with a minor omission or a little too much detail.
- **9-10** - Two sentences or fewer, every claim traceable to the email, and enough for a reviewer to triage without opening it.

---

### ENQ-001

**Customer email**

```
Subject: Question about the figures on my annual statement (policy HKL-62397257)

Hi,

I got the annual statement for my whole life policy (no. HKL-62397257) in the post last week and have a couple of questions about the numbers. I've had this plan since about 2015 and honestly I usually just file the statement away, but this year I actually sat down and read it properly.

Could you explain the difference between the "Guaranteed Cash Value" column and the "Total Projected Value" column? The total is quite a bit higher than the guaranteed part and I'm not sure what makes up the difference - is that the dividends part? Also, the projected figure shown for future years, is that something I can actually rely on for planning, or can it go down as well as up?

No rush on this, I'm just trying to get my finances a bit more organised this year and want to understand what I'm looking at.

Thanks,
Wong Mei Ling
Flat 6A, 9/F, Fortune Garden, 88 Sample Road, Tsuen Wan
Tel: 96692460
```

**Summary written for the reviewer**

> The customer asks for an explanation of the difference between 'Guaranteed Cash Value' and 'Total Projected Value' on their annual statement for policy HKL-62397257. They also inquire about the reliability of projected figures for financial planning and whether these values can decrease.

**Draft reply**

```
Dear Ms. Wong,

Thank you for contacting us regarding your annual statement for policy number HKL-62397257. We are happy to help clarify the figures presented in your document.

The "Guaranteed Cash Value" represents the minimum amount that is contractually guaranteed by the insurer, regardless of market performance or other factors. The "Total Projected Value" includes this guaranteed amount plus any non-guaranteed benefits, such as dividends or bonuses, which are projected based on current assumptions.

Regarding your question about reliability, please note that the non-guaranteed portion of the Total Projected Value is not guaranteed and may vary. These projections are based on our current assumptions about future investment returns and other factors, but actual results may be higher or lower. Therefore, while these figures can be useful for general planning purposes, they should not be relied upon as certain outcomes, as the value can indeed go down as well as up depending on actual performance.

For a more detailed breakdown specific to your policy, we recommend reviewing the "Policy Illustration" section of your annual statement or contacting your financial advisor if you have one assigned.

If you have any further questions or require additional clarification, please do not hesitate to contact us.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-002

**Customer email**

```
Subject: Enquiry abt my whole life policy statement - dividend question

Hi Customer Service,

Sorry to bother you, I recieved the anniversary statement for my policy last week (policy no. WL-60705385, holder Chan Tai Man) and have a few questions, hope you can help.

On the statement it shows "Guaranteed Cash Value", then "Non-guaranteed Dividend" and also something called "Terminal Bonus". 我唔係好明 the difference between these. Is the dividend amount shown money that is already inside my policy, or is it just a projection? If a dividend is already credited, can it be reduced later, or once credited it wont change?

Also, my agent told me years ago that the total cash value around year 20 would be roughly HK$500k, but the figures on this statement look lower than what I remember from the sales illustration. 唔知係咪我睇錯咗. Could you send me an updated benefit illustration so I can compare against the original one?

One more small question: if one day I want to withdraw part of the accumulated dividends but keep the policy running, is that allowed? I am NOT planning to do this now, just want to understand my options, so no rush at all.

Thanks alot!

Regards,
Chan Tai Man (陳大文)
Tel: 93092875

--
Tai Man Chan | Senior Logistics Coordinator
Everbloom Trading (HK) Limited
18/F, Sunshine Plaza, 111 King's Road, Quarry Bay, Hong Kong
Tel: +852 91909112 | Fax: +852 93495541

This e-mail and any attachment is confidential and intended solely for the addressee. 本電郵及附件只供指定收件人閱讀。 If you received this message in error, please notify the sender and delete all copies. Please consider the environment before printing this email.
```

**Summary written for the reviewer**

> The policyholder seeks clarification on the definitions and stability of Guaranteed Cash Value, Non-guaranteed Dividend, and Terminal Bonus shown in their recent statement. They also request an updated benefit illustration to compare with previous projections and inquire about the possibility of partial dividend withdrawals while keeping the policy active.

**Draft reply**

```
Dear Mr. Chan,

Thank you for your email regarding your whole life policy (No. WL-60705385). We are happy to clarify the terms on your anniversary statement and address your questions.

Regarding the components of your policy value:

1. **Guaranteed Cash Value**: This is the minimum cash value guaranteed by the insurer, as stated in the policy contract. It will not decrease.
2. **Non-guaranteed Dividend**: These dividends are declared annually based on the performance of the participating fund. Once a dividend is credited to your policy, it becomes part of the guaranteed cash value and cannot be reduced or taken back. However, future dividend declarations are not guaranteed and may vary.
3. **Terminal Bonus**: This is a one-off bonus that may be payable upon claim settlement (e.g., death or maturity). It is non-guaranteed and depends on the investment performance and other factors at the time of the claim. It is not available for withdrawal during the policy term.

You mentioned that the current figures appear lower than the sales illustration provided years ago. Sales illustrations are based on assumed rates of return and are for reference only; actual performance may differ. To help you review your policy's current status, we can prepare an updated benefit illustration for you. Please note that this updated illustration will also be based on current assumptions and is not a guarantee of future performance.

Regarding your question on withdrawals: Yes, it is generally possible to withdraw part of the accumulated dividends (if they have been credited as cash) while keeping the policy in force. However, such withdrawals may affect the future growth of your policy value and bonuses. Specific terms and conditions apply, and we recommend discussing your specific needs with our team or your agent before making any decisions.

To proceed with sending you the updated benefit illustration, please confirm if you would like us to send it via email or post. For security purposes, we may need to verify your identity before releasing detailed policy documents.

If you have further questions, please feel free to contact us.

Yours sincerely,

Customer Service Team
[Insurer Name]
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-008

**Customer email**

```
Subject: How do I update the address on my policy?

Hi,

We moved from our old place in Tai Wai to Tseung Kwan O a few weeks ago and I keep meaning to update the address on my life policy (PL-12900796) before anything gets posted to the old flat.

Could you tell me how to do it? Is it something I can do myself on the online portal, or do I need to fill in a form and post it in? And will you need any proof of the new address, like a bank statement or utility bill in my name?

Also does the address on file make any difference to the premium or anything else on the policy? I assume not but thought I'd double check.

No urgency at all, I can still be reached by email in the meantime.

Thanks,
Michelle Wong
customer3870@example.com
```

**Summary written for the reviewer**

> The customer requests instructions for updating the residential address on policy PL-12900796 from Tai Wai to Tseung Kwan O. She asks about the procedure, required documentation, and potential impact on premiums.

**Draft reply**

```
Dear Michelle,

Thank you for contacting us regarding your life policy (PL-12900796).

You can update your residential address through our online customer portal or by submitting a completed Change of Particulars form. If you choose to use the form, please return it to us via post or email.

Regarding documentation, we may require proof of your new address, such as a recent utility bill or bank statement in your name, to verify the change. Our team will advise if this is necessary during the processing of your request.

Please be assured that updating your residential address does not affect your policy premium or coverage terms.

If you would like to proceed via the online portal, please log in to your account and navigate to the 'Profile Settings' section. Alternatively, I can send you the relevant form if you prefer.

Should you have any further questions, please do not hesitate to contact us.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-009

**Customer email**

```
Subject: address change follow up + questions (P-50535032 / P-76676583)

Hi Customer Service,

Sorry to bother you again - I sent the email below last week but so far only got the automated acknowlegement, so I'm following up here in case it got lost.

I finally 搬咗屋 last month and want to update the address on my file. My details:

Name: Chan Wing Sze
Policy 1 (whole life): P-50535032
Policy 2 (hospital income rider): P-76676583

New address:
Room 1807, Tower 2, Sunset Heights
88 Unicorn Street, Tai Kok Tsui
Kowloon

A few qeustions:

1. Can I change the address in your mobile app, or do I have to fill in a form? If there's a form, which one is it, and can I email a scanned copy instead of posting it?
2. Do you need proof of address? The problem is the utility bills at the new flat are still in the landlord's name. I do have a bank statement showing the new address - would that be acceptable?
3. Will one change of address cover both policies, or do I need to submit it seperately for each one?

No rush at all, just want to get this sorted before I forget again. 唔該晒！

Best regards,
Wing Sze

Wing Sze Chan | Senior Accounts Clerk
Everglow Textile Trading Company Limited
Unit 6, 11/F, Harbour Industrial Centre, 55 Fictitious Street, Kwun Tong, Kowloon
Tel: +852 96337794 | Mobile: 96437530 | Email: customer5279@example.com
This message and any attachment are confidential and intended solely for the named recipient. If you have recieved it in error, please notify the sender and delete all copies. Please consider the environment before printing this email.

---------- Forwarded message ----------
From: Wing Sze Chan <customer5279@example.com>
Date: Mon, 28 Oct 2024 at 14:03
Subject: address change - policy P-50535032
To: customer3826@example.com

Dear Sir/Madam,

I have recently moved house and would like to change the address on my policy P-50535032. Please let me know the procedure and what documents you need.

Thank you,
Wing Sze Chan

From: No-Reply <customer9601@example.com>
Date: Mon, 28 Oct 2024 at 14:03
Subject: RE: address change - policy P-50535032 (Ref: ENQ-11241016)
To: customer5279@example.com

Thank you for your email. This is an automated acknowledgement. Your enquiry reference is ENQ-11241016. Please do not reply to this message.
```

**Summary written for the reviewer**

> The customer requests to update the address for two policies (P-50535032 and P-76676583) and asks about the submission method, acceptable proof of address, and whether one update covers both policies. The customer notes that utility bills are in the landlord's name but offers a bank statement as alternative proof.

**Draft reply**

```
Dear Ms Chan,

Thank you for your email regarding the address update for your policies P-50535032 and P-76676583.

To answer your questions:

1. **Submission Method**: You can update your address via our mobile app or by submitting a completed Change of Particulars form. If you prefer to use a form, you may email a scanned copy to us; posting is not required.

2. **Proof of Address**: We generally require a recent utility bill, government letter, or bank statement issued within the last three months. A bank statement showing your new address is acceptable even if the utility bills are in your landlord's name.

3. **Coverage**: One successful address update will apply to all policies held under your name, so you do not need to submit separate requests for each policy.

Please let us know if you would like us to send you the Change of Particulars form, or if you prefer to proceed via the mobile app.

Best regards,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-010

**Customer email**

```
Subject: Question about updating home address on my policy

Hi,

We moved flat last month and it's only just occurred to me that I never updated the address on my life policy (policy no. L-26398571, under Marco Cheung Ka Ho).

Could you let me know how to go about changing it? A few things I'm wondering:

- Can I do it through the online portal or your app, or do I need to fill in a physical form and post it?
- Do you need proof of the new address, e.g. a utility bill or bank statement?
- My wife has a small savings plan that I believe sits under the same account — does her address update along with mine or does she need to submit her own request?
- Will changing the address affect the premium or anything else on the policy?

For reference the new address is Flat 12C, Tower 3, Greenfield Court, 88 On Chun Street, Ma On Shan, NT.

No particular rush, just want to get it sorted when convenient.

Thanks,
Marco Cheung
Mobile: 97979951
```

**Summary written for the reviewer**

> The customer requests instructions to update the home address for policy L-26398571 and asks if online updates are possible, what proof is required, and if the change affects premiums. The customer also enquires whether a separate savings plan held by his wife under the same account requires a distinct address update request.

**Draft reply**

```
Dear Mr Cheung,

Thank you for contacting us regarding the update of your residential address for policy number L-26398571.

To ensure your records remain accurate, please find the answers to your questions below:

1. **How to update:** You can update your address through our online portal or mobile app by logging into your account and navigating to the 'Profile' or 'Personal Details' section. Alternatively, you may complete a Change of Particulars form, which is available on our website, and submit it via post or email.

2. **Proof of address:** For standard address updates, we typically do not require supporting documents such as utility bills unless specifically requested during the verification process. However, please keep a recent proof of address handy in case it is needed.

3. **Impact on policy:** Updating your residential address does not affect your premium rates or policy benefits. It ensures that all future correspondence reaches you correctly.

4. **Separate policy for your wife:** As insurance policies are individual contracts, your wife’s savings plan will require a separate address update request. Even if linked to the same master account for administrative purposes, personal details must be updated for each policyholder individually. She can follow the same steps mentioned above via the online portal or by submitting her own form.

If you encounter any difficulties using the online services or prefer assistance with the forms, please feel free to contact our customer service hotline at [Insert Hotline Number] during business hours.

Thank you for keeping your details up to date.

Yours sincerely,

Customer Service Team
[Insurer Name]
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-014

**Customer email**

```
Subject: Premium debited this month is higher than before - policy L-94818000

Hello,

Hope you can help me figure this out. I was going through my HSBC credit card statement and noticed the premium autopay for my policy (no. L-94818000, under Cheung Ka Ho Kelvin) went through on 3 Oct as HK$2,347.80. I'm fairly sure it used to be around HK$2,310 a month, at least that's what I remember from my statements earlier this year.

I took out the plan back in 2019, I believe it's a whole life policy with a critical illness rider attached. I always assumed the premium just stayed the same every month, so the change caught me a bit off guard.

Could you let me know:
1. Why the amount went up
2. A breakdown of what the monthly premium actually consists of (base premium, the rider, and that insurance levy thing - does the levy rate change every year?)
3. Whether HK$2,347.80 is what I should expect from now on

No rush on this, I just want to understand my own bill properly. Email reply is fine, or you can call me on 97094910 after 7pm on weekdays.

Thanks,
Kelvin Cheung
```

**Summary written for the reviewer**

> The policyholder queries a recent increase in the autopay premium amount for policy L-94818000, noting a difference from previous payments. He requests an explanation for the change, a breakdown of the premium components including the insurance levy, and confirmation of future payment amounts.

**Draft reply**

```
Dear Mr Cheung,

Thank you for your email regarding the premium debit for policy L-94818000.

We understand your concern about the change in the autopay amount and would be happy to clarify the details for you. To provide an accurate explanation for the difference in the charged amount and a breakdown of the current premium components (including the base premium, rider costs, and any applicable levies), we need to review the specific terms and billing history associated with your policy.

Our team will look into this and contact you at 97094910 after 7pm on a weekday to discuss the details, as requested. Alternatively, if you prefer to receive this information via email, please let us know and we will send the breakdown to you directly.

Should you have any further questions in the meantime, please do not hesitate to contact us.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-015

**Customer email**

```
Subject: premium deducted twice this month?? policy LHK-81292572

Hi Customer Service,

I checked my bank statement this morning and saw my life insurance premium got dedcuted TWICE this month, both HK$1,872.00:

- 3 June
- 17 June

My policy no. is LHK-81292572 (CHAN Tai Yan, Iris). Usually the autopay only goes out once on the 3rd, been like that for 2 years already. I never asked for any extra payment and I didn't change anything on the policy as far as I know. 唔該幫我check吓係咪收多咗?

If it is really a double charge, how do I get the money back? Will it go back into my bank account automatically or do I need to fill in some form?

You can call me on 97717742 if that's easier, afternoon better as I have meetings in the morning.

Thanks,
Iris Chan
Senior Marketing Executive
BrightPeak Media Ltd

Sent from my iPhone
```

**Summary written for the reviewer**

> The customer reports two premium deductions of HK$1,872.00 for policy LHK-81292572 in June and requests verification of a potential double charge. She also enquires about the refund procedure if an overpayment is confirmed.

**Draft reply**

```
Dear Ms Chan,

Thank you for contacting us regarding your premium payments for policy LHK-81292572.

We have received your enquiry concerning the two deductions of HK$1,872.00 on 3 June and 17 June. We are currently reviewing your payment records to verify the status of these transactions.

Once our review is complete, we will contact you to explain the findings. If an overpayment is confirmed, we will provide you with the necessary details regarding the refund process at that time.

Should we require any further information from you, we will reach out via the phone number provided (9771 7742), preferably in the afternoon as requested.

Thank you for your patience.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-021

**Customer email**

```
Subject: Day surgery claim - what do you need from me?

Hi,

Hope you can point me in the right direction. I'm probably going to have a knee scope done (doctor called it an arthroscopy) as a day procedure sometime early next year. Nothing is booked yet, no urgency at all, I just like getting my paperwork sorted ahead of time.

The policy is a hospital plan under my name, Chan Tai Man, policy no. HK-40923280.

A few things I couldn't find clear answers to on your website:

1. For a day surgery, can I submit the claim through the mobile app, or do I have to post the original receipts to your office? I read somewhere originals are needed but the app seems to let you upload photos so I'm confused.
2. What documents do you normally want from the hospital? Is the discharge summary enough, or do I also need the itemised bill and the doctor's report?
3. Do I need to notify you before the surgery happens, or do I just claim afterwards?

Like I said, no rush on this, the operation isn't even scheduled. Just want to know what bits of paper to hang on to.

Thanks,
Chan Tai Man
Flat 8, 12/F, Block C, Sunshine Gardens, Ma On Shan, NT
```

**Summary written for the reviewer**

> The policyholder, Chan Tai Man (Policy No. HK-40923280), enquires about documentation and submission procedures for an upcoming knee arthroscopy day surgery claim. He specifically asks about mobile app submission versus posting originals, required hospital documents, and whether pre-notification is necessary.

**Draft reply**

```
Dear Mr. Chan,

Thank you for contacting us regarding your upcoming knee arthroscopy. We are happy to provide guidance on the claim process to help you prepare your documents in advance.

Regarding your questions:

1. **Submission Method**: You may submit claim documents via our mobile app by uploading clear photos of the required paperwork. However, please note that we may request the original receipts and documents for verification purposes depending on the claim assessment. It is advisable to keep all original documents safe until the claim is fully settled.

2. **Required Documents**: For day surgery claims, we typically require the following:
   - Completed claim form (available on our website or app)
   - Original itemised bill(s) from the hospital/clinic
   - Original receipt(s) showing proof of payment
   - Discharge summary or medical report detailing the procedure and diagnosis
   - Any relevant test results or doctor's notes related to the surgery

3. **Pre-notification**: While pre-notification is not strictly mandatory for day surgery under most hospital plans, we recommend informing us prior to admission if your policy includes a cashless arrangement or if you wish to confirm coverage details beforehand. This can help streamline the process. You may contact our customer service hotline or use the app to check your specific plan benefits.

Please ensure that all documents clearly show your name, policy number, and the details of the treatment. If you have any further questions or need assistance with the claim form, feel free to reach out to us.

We wish you a successful procedure and a speedy recovery.

Yours sincerely,

Customer Service Team
[Insurer Name]
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-022

**Customer email**

```
Subject: How to claim for day surgery - first time claiming

Hi there,

I had a day surgery done at St Teresa's Hospital last tuesday (removal of a small cyst on my back, nothing serious don't worry). The bill came to about HK$38,000 and I paid it by credit card first.

I've never made a claim before so I'm not really sure how this works. My policy is the hospital plan, number VHL-30542581, under my name Carman Tsui Hoi Yan.

Can you tell me:
1. what form do I need to fill in and where do I get it
2. does my doctor need to sign or fill in anything, or is the hospital receipt on its own enough
3. can I submit everything online or do I have to post the original receipts? I only have one set of the originals so I'm a bit worried about putting them in the mail
4. roughly how long before I get the money back

One more thing - I have a follow up appointment with the doctor next month. Do I need to inform you before I go, or can I just claim it afterwards like this one?

Thanks a lot,
Carman Tsui
92240893
```

**Summary written for the reviewer**

> The customer, Carman Tsui, is submitting her first claim for day surgery at St Teresa's Hospital and requires guidance on forms, documentation, submission methods, and processing times. She also asks if pre-notification is required for an upcoming follow-up appointment.

**Draft reply**

```
Dear Ms. Tsui,

Thank you for contacting us. We are glad to hear that your procedure went well.

Regarding your enquiry about claiming for your recent day surgery, please find the answers to your questions below:

1. Claim Form: You will need to complete a Medical Claim Form. This can be downloaded from our website under the 'Forms' section or requested by calling our Customer Service Hotline.

2. Doctor's Certification: In addition to the original receipts and detailed bill from St Teresa's Hospital, the attending doctor usually needs to complete the medical certification section of the claim form to confirm the diagnosis and treatment details.

3. Submission Method: To protect your original documents, we recommend submitting clear scanned copies or photos of all documents via our online portal or mobile app. However, please note that we may request the original receipts for verification purposes later. If you prefer to post them, we suggest using registered mail. If originals are required, they will be returned to you after processing.

4. Processing Time: The time required to process a claim varies depending on the complexity of the case and whether additional information is needed. We will notify you once the assessment is complete.

Regarding your follow-up appointment next month, you generally do not need to inform us beforehand. You can submit the claim for that visit afterwards using the same process.

If you have further questions or need assistance with the online submission, please feel free to contact us.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-023

**Customer email**

```
Subject: Hospital claim - what do I need to send in? (policy LA-23537347)

Hi,

Writing about my policy LA-23537347 (under my name, Cheung Wai Sze). I was in a private hospital in Mong Kok for 4 nights last month for gallbladder surgery, discharged on 18 June, and I want to put in a claim under the hospital cash benefit. Never claimed before so can you tell me:

1) what documents you actually need - I have the discharge summary and the itemised hospital bill, is that enough or do I need to get a doctor's report as well?
2) where to send it - can I just upload copies or do you need originals by post?
3) roughly how long the assessment takes?

While I'm here - I tried your app twice last week to start the claim and both times it crashed right at the photo upload step and wiped everything I'd typed in, which was infuriating. Also called the hotline on Tuesday afternoon and sat on hold for over 40 minutes before giving up. Not really good enough when you're recovering from surgery and just want a straight answer. Someone should probably look into both of those.

But the main thing is the claim itself - if you can let me know the above I'll get everything sent off properly this time.

Thanks,
Winnie Cheung
96487556
```

**Summary written for the reviewer**

> The customer seeks guidance on required documents, submission method, and assessment timeline for a hospital cash benefit claim under policy LA-23537347. They also reported technical issues with the mobile app and long wait times on the hotline.

**Draft reply**

```
Dear Ms Cheung,

Thank you for contacting us. We are sorry to hear about your recent surgery and hope you are recovering well.

Regarding your claim for the hospital cash benefit, we acknowledge your policy number LA-23537347. To assist you with the submission, please note the following:

1. **Required Documents**: While the discharge summary and itemised hospital bill are essential, additional medical reports may be required depending on the specific terms of your policy. We recommend submitting all available medical records related to the admission to ensure a complete review.

2. **Submission Method**: You may submit clear copies of the documents via our online portal or mobile app. Originals are generally not required unless specifically requested during the assessment process. If you prefer to send physical copies, please mail them to our claims department address listed on our website.

3. **Assessment Timeline**: The time required to assess a claim varies based on the complexity of the case and the completeness of the documentation provided. We will notify you once the review is complete.

We sincerely apologize for the frustration caused by the technical issues with our app and the long wait time on our hotline. Your feedback regarding the app crash during photo upload and the hold time has been recorded and will be shared with our technical and customer service teams for investigation and improvement.

If you encounter further difficulties with the digital submission, please feel free to reply to this email with the attached documents, and we will guide you through the next steps.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-028

**Customer email**

```
Subject: Complaint about my policy P-67155454 - cash value far below what agent told me

Dear Sir/Madam,

I am writing to complain about my policy P-67155454, a Lifelong Treasure Whole Life Plan I took out in 2019 through your agent Mr Kelvin Yeung.

When I signed up, Kelvin sat with me at your Mong Kok branch and explained that by around year 5 the policy would more or less "breakeven", meaning I could get back roughly what I had put in. I remember this clearly because I asked him twice. He kept pointing at the projection columns and never properly explained what was guaranteed and what was not.

I have now paid about HK$180,000 in total premiums (HK$36,000 a year). The anniversary statement I received last week shows a surrender value of only around HK$121,400. That is a shortfall of almost HK$60,000. Honestly I feel misled and quite upset about it.

I would like the following please:

1. A proper written explanation of why the surrender value is so much lower than the premiums paid, and which figures are guaranteed versus non-guaranteed.
2. A copy of the benefit illustration I signed at the time of application, so I can compare it with what I was told.
3. An explanation of my options now - what happens if I surrender, if I stop paying premiums, or if I keep the policy going. Nobody warned me that stopping early would cost this much.

I also want this registered as a formal complaint about how the plan was sold to me, not just a general enquiry. Please confirm it has been logged and explain how your complaint process works, including what happens if I am not satisfied with your answer.

Regards,
Chan Ka Yan (Ms)
Mobile: 90562030
Flat 6B, 12/F, Mayfair Court, 18 Goldfinch Road, San Po Kong, Kowloon
```

**Summary written for the reviewer**

> The customer complains that the surrender value of policy P-67155454 is significantly lower than the premiums paid, alleging misrepresentation by the selling agent regarding breakeven timelines. She requests a formal complaint registration, an explanation of guaranteed versus non-guaranteed values, a copy of the original benefit illustration, and details on her policy options.

**Draft reply**

```
Dear Ms Chan,

Thank you for your email regarding policy P-67155454. We have received your message and registered it as a formal complaint concerning the sales process and the current surrender value of your Lifelong Treasure Whole Life Plan.

We take allegations of mis-selling seriously. Our Complaints Handling team will review your case, which includes examining the benefit illustration provided at the time of application and the notes from your interaction with our agent. We will provide a written response addressing your specific questions regarding the difference between guaranteed and non-guaranteed benefits, as well as the options available to you should you choose to surrender the policy, stop premium payments, or continue coverage.

As part of this investigation, we will also arrange to provide you with a copy of the benefit illustration signed during the application process for your reference.

We will acknowledge receipt of this formal complaint in writing separately, outlining the next steps and the expected timeline for our full response in accordance with our complaints handling procedures. If you are not satisfied with our final response, that acknowledgment will also explain your right to refer the matter to the Insurance Complaints Bureau.

Should you have any immediate questions while we conduct our review, please do not hesitate to contact us.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-029

**Customer email**

```
Subject: Formal complaint - appalling hotline service on 12 March

Dear Sir/Madam,

I want to make a formal complaint about how I was treated on your customer service hotline on 12 March.

I called at around 2:30pm and sat on hold for over 35 minutes. When someone finally picked up, I got about two sentences out before I was put on hold again and transferred. In total I was transferred three times, and each time I had to explain everything from the start because clearly nobody was passing any notes on. The last man I spoke to would not give me his name, told me my issue was "not his department", and said a supervisor would call me back the same day. Nobody called.

On 14 March I phoned again to chase the callback and was told there was no record of my call on the 12th at all. No record. So apparently the 35 minutes on hold and three transfers never happened as far as your company is concerned.

To be clear, my actual question was eventually answered through your WhatsApp chat, so that part is done. That is not why I am writing. I am writing because the whole thing was appalling. I have had my policy with you for nine years (policy no. LHK-46261940) and I have never been treated like this - bounced from person to person, promised a callback that never came, then told the call basically doesn't exist.

I want this properly acknowledged in writing. I want an explanation of why my call was never logged and why the promised callback never happened, and I want to know what is actually being done so this doesn't keep happening to other people. Please do not send me the usual copy-paste "we value your feedback" reply, because that will just make me angrier.

Regards,
Chan Tai Man
Policy no. LHK-46261940
```

**Summary written for the reviewer**

> The customer complains about poor hotline service on 12 March, including long hold times, multiple transfers without note-passing, and a failed callback promise. They state their original query was resolved via WhatsApp but demand a written acknowledgment, an explanation for the missing call record, and details on corrective actions.

**Draft reply**

```
Dear Mr Chan,

Thank you for contacting us. We sincerely apologize for the frustrating experience you encountered with our hotline service on 12 March and for the distress caused by the lack of follow-up.

We take your feedback seriously, particularly regarding the unlogged call and the missed callback promise. Your comments have been escalated to our Customer Service Management team for a thorough investigation into why the call record was not retained and why the agreed-upon callback did not occur.

A member of our management team will review the specifics of your case and contact you directly in writing to provide a detailed explanation and outline the steps we are taking to prevent similar issues in the future. We appreciate your patience while we conduct this review.
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-030

**Customer email**

```
Subject: Complaint - change of address still not done after two submissions

To whom it may concern,

I am writing to formally complain about how a simple change of address request has been handled, because frankly this has been a ridiculous waste of my time.

My name is Leung Wai Sze and my policy number is LHK-60137580 (whole life plan taken out in 2014). I moved in May and posted my completed change of particulars form on 20 May. I heard nothing back, so I called your hotline on 10 June. After 25 minutes on hold and being transferred twice, the agent told me the form was "not received" and asked me to send it again. I emailed a scanned copy the same day, with my new address: Flat 12B, Tower 3, Sunrise Gardens, 88 Fictitious Road, Ma On Shan, New Territories.

Then last week my premium notice turned up at my OLD address and my mother had to forward it to me. When I called again I was told the form was received after all, but "not yet processed". So which is it? Does anyone there actually write anything down?

I have been paying premiums for ten years and have never missed one. Every call to your hotline costs me half my lunch break and I end up repeating the whole story to a different person each time. This is honestly the worst service I have had from any company in years.

What I want:
1. My correspondence address updated to the one above, with written confirmation sent to me once it is done.
2. An explanation of what happened to my first form sent in May.
3. All future documents, including my annual statement, sent to the new address.

Please do not ask me to fill in the same form a third time.

Very dissatisfied,
Leung Wai Sze
Tel: 90055081
```

**Summary written for the reviewer**

> The customer complains about a delayed address change for policy LHK-60137580 despite two submissions. They request confirmation of the update to Flat 12B, Tower 3, Sunrise Gardens, an explanation for the delay, and assurance that future documents will be sent to the new address.

**Draft reply**

```
Dear Ms Leung,

Thank you for your email. We sincerely apologise for the frustration and inconvenience caused by the delay in updating your correspondence address and for the inconsistent information you received from our hotline.

We have escalated your case to our operations team to immediately verify the status of your request and ensure your address is updated to Flat 12B, Tower 3, Sunrise Gardens, 88 Fictitious Road, Ma On Shan, New Territories. We will also investigate what happened to the form submitted in May to provide you with a clear explanation.

Once the update is confirmed, we will send you written confirmation and ensure that all future documents, including your annual statement, are directed to your new address. You do not need to submit the form again.

We aim to resolve this matter promptly and will contact you with an update as soon as possible.

Yours sincerely,
Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-035

**Customer email**

```
Subject: Please take me off your marketing call and email lists

Hi there,

My name is Karen Chan Ka Yan and I have a life policy with your company (I don't have the policy number on hand, but my registered mobile is 99455740 and email is customer4433@example.com).

For the past few months I've been getting regular sales calls from your agents about new savings plans, plus promotional emails almost every week. The calls usually come during work hours which is a bit inconvenient.

Just to be clear, I'm happy with my policy and this isn't a complaint. I simply don't want to receive any more marketing calls or promotional emails. Could you please remove my number and email address from your marketing and telemarketing lists?

If you need me to confirm anything or fill in a form, just let me know.

Thanks,
Karen
```

**Summary written for the reviewer**

> The customer requests removal from marketing call and email lists. She provided her name, mobile number, and email address for identification but does not have her policy number.

**Draft reply**

```
Dear Ms. Chan,

Thank you for contacting us.

We have received your request to remove your mobile number (99455740) and email address (customer4433@example.com) from our marketing and telemarketing lists. We appreciate your feedback regarding the timing of these communications.

Our team will process this update in accordance with our data privacy procedures. Please note that while we act promptly, it may take a short period for the changes to take effect across all our systems. You will continue to receive essential service communications related to your policy, such as premium notices or policy updates, as these are distinct from marketing materials.

If you have any further questions, please feel free to contact us.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |

---

### ENQ-036

**Customer email**

```
Subject: Data access request - copy of my personal data (policy L-39799712)

Hello,

I would like to make a data access request under the Personal Data (Privacy) Ordinance (Cap. 486). Please provide me with a copy of all personal data your company holds about me. As far as I understand this would include things like my original application and underwriting forms, policy and servicing records, correspondence, call recordings and any internal notes on my file, but I am asking for everything, not just those items.

I would also like to know which third parties my personal data has been disclosed to over the years, if any - for example reinsurers, banks, agents, or any marketing partners. If it has never been disclosed to anyone, please confirm that too.

My details for verification:
Name: Chan Mei Ha
Policy number: L-39799712 (whole life plan, taken out around 2016)
HKID: X663413(A) - happy to provide a copy if required
Address: Flat 5B, 14/F, Block 2, Harbour View Gardens, 123 Sample Road, Ma On Shan, NT

Please let me know if there is a standard form I need to complete and whether any charge applies. You can reply to this email or reach me on 92630147.

Thank you,
Chan Mei Ha
```

**Summary written for the reviewer**

> The customer requests access to all personal data held under policy L-39799712 and details of third-party disclosures. She provides verification details and asks about required forms or charges.

**Draft reply**

```
Dear Ms Chan,

Thank you for your email regarding your data access request for policy L-39799712.

To ensure the security of your personal information, we require a completed Data Access Request Form along with a copy of your Hong Kong Identity Card for verification purposes. Please find the standard form attached to this email.

Regarding your enquiry on fees, there is generally no charge for complying with a data access request, unless the request is excessive in nature. We will assess this once we receive your completed form.

Upon receipt of the verified request, our team will process it in accordance with the Personal Data (Privacy) Ordinance. We will contact you if further information is required during the process.

Should you have any questions, please feel free to contact us.

Yours sincerely,

Customer Service Team
```

| dimension | your score 0-10 |
|---|---|
| commitment groundedness | |
| tone match | |
| summary quality | |
